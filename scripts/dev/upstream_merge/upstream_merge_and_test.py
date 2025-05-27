import datetime
import os
import argparse
import logging
from json_config import json_config
from GitRepo import *
from git_commands import send_email
from upstream_merge import merge_submodules_with_upstream
from build import build_images
from test import OS_test
from push_and_PR import push_and_PR_prepare

def parse_args():
    parser = argparse.ArgumentParser(description="Automated repository merging script")
    parser.add_argument("-c", type=str, help="Path to configuration file", default="scripts/dev/upstream_merge/automation_conf.json")
    parser.add_argument("-w", type=str, help="Skip merging with upstream", default=None)
    parser.add_argument("-s", type=str, help="Skip merging with upstream", default=False)
    args = parser.parse_args()

    return args

def setup_logging(log_level=10):
    """
    Set up logging configuration.
    :param log_file_name: Name of the log file.
    :param log_level: Logging level (default: 10).
    """
    os.makedirs(f"temp/{datetime.datetime.now().strftime('%d-%m-%Y')}", exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"temp/{datetime.datetime.now().strftime('%d-%m-%Y')}/upstream_merge_{datetime.datetime.now().strftime('%H-%M-%S')}.log", mode='a')
        ]
    )
    
def write_email_addresses(email_log_file_name, email_from, email_to):
    with open(email_log_file_name, "w") as log:
        log.write(f"From: {email_from}\n")
        log.write(f"To: {email_to}\n")
        log.write("Subject: Merge Details\n\n")

def format_status(status, message):
        if status != 0:
            return " ... ERRORS", f" ... ERRORS\n    {message or ''}\n", f" ... ERRORS\n    {message or ''}\n\n\n"
        elif message is None:
            return " ... OK (no changes)", "", " ... OK (no changes)\n\n\n"
        else:
            return " ... OK", "", f" ... OK\n    {message}\n\n\n"
        
def format_merge_report(merge_report, email_log_level):
    """
    The formatted report string is structured as follows:
    - The first line contains the repository name.
    - The second line contains the status of the merge (OK, ERRORS, or no changes).
    - The diff are added if there are any changes and if email_log_level is set to 1.

    Merge completed successfully:
    sources/bitbake
     ... OK
         Push and PR ... OK

    No changes were detected during the merge:
    sources/bitbake
     ... OK (no changes)

    Errors occurred during the merge:
    sources/bitbake
     ... ERRORS
    """
    min_detail = ""
    error_detail = ""
    diff_detail = ""

    build_and_test_detail = merge_report.pop("Build and Test")
    if build_and_test_detail[0] == 0:
        push_and_PR_details = merge_report.pop("Push and PR")    

    for git_obj, (status, message) in merge_report.items():
        min_line, error_line, additional_line = format_status(status, message)
        min_detail += f"{git_obj.local_repo}\n{min_line}\n"
        if error_line != "":
            error_detail += f"{git_obj.local_repo}\n{error_line}\n"
        diff_detail += f"{git_obj.local_repo}\n\n{additional_line}"
        if build_and_test_detail[0] == 0 and status == 0 and message is not None:
            git_obj_push_details = push_and_PR_details[git_obj]
            if git_obj_push_details[0] == 0:
                min_detail += "     Push and PR ... OK\n"
                diff_detail += f"     Push and PR ... OK\n"
            else:
                min_detail += "     Push and PR ... ERRORS\n"
                error_detail += f"{git_obj.local_repo}\n{min_line}\n     Push and PR ... ERRORS\n    {git_obj_push_details[1]}\n"
                diff_detail += f"     Push and PR ... ERRORS\n    {git_obj_push_details[1]}\n"
    
    min_detail += "Build and Test\n"
    if build_and_test_detail[0] == 0:
        min_detail += " ... OK\n"
        diff_detail += f"\nBuild and Test\n ... OK\n    {build_and_test_detail[1]}\n"
    else:
        min_detail += " ... ERRORS\n"
        error_detail += f"\nBuild and Test\n ... ERRORS\n    {build_and_test_detail[1]}\n"
        diff_detail += f"\nBuild and Test\n ... ERRORS\n    {build_and_test_detail[1]}\n"
    
    if email_log_level == 0:
        return min_detail + "\n\n" + error_detail
    return min_detail + "\n\n" + error_detail + "\n\n" + diff_detail

def write_log(email_log_file_name, contents):
    with open(email_log_file_name, "a") as log:
        log.write(contents)

def write_log_and_send_email(email_from, email_to, merge_report, email_log_level):
    email_log_file_name = f"temp/{datetime.datetime.now().strftime('%d-%m-%Y')}/upstream_merge_{datetime.datetime.now().strftime('%H-%M-%S')}.txt"
    formatted_report_string = format_merge_report(merge_report,email_log_level)
    write_email_addresses(email_log_file_name, email_from, email_to)
    write_log(email_log_file_name, formatted_report_string)
    send_email(to=email_to, subject="Merge Details", file=email_log_file_name)

def build_and_test(clean_build, vm_name, snapshot_name, merge_has_errors):
    if merge_has_errors == True:
        return (1,"Merge has Errors")
    success = build_images(clean_build)
    if success[0] != 0:
        return success
    success = OS_test(vm_name, snapshot_name)
    return success

def pull_from_base_branch(branch,upstream_URL):
    """
    Pull the latest changes from the NILRT repository.
    """
    git_obj = GitRepo()

    add_remote_details = git_obj.add_remote("upstream",upstream_URL)
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details
    
    pull_latest_details = git_obj.pull_latest(branch,"upstream")
    if pull_latest_details[0] != 0:
        print(pull_latest_details[1])
        return pull_latest_details
    
    return (0,None)

def update_meta_nilrt_branch(meta_nilrt_branch):
    """
    Pull the latest changes from the meta-nilrt repository.
    """
    os.chdir("sources/meta-nilrt")
    pull_from_meta_nilrt_details = pull_from_base_branch(meta_nilrt_branch,"https://github.com/ni/meta-nilrt.git") # To ensure that the meta-nilrt branch is up to date
    if pull_from_meta_nilrt_details[0] != 0:
        print(pull_from_meta_nilrt_details[1])
        return pull_from_meta_nilrt_details
    os.chdir("../..")
    
    return (0,None)

def main():
    args = parse_args()
    skip_merge = args.s

    json_config_obj = json_config(automation_conf_path=args.c,workitemID=args.w)    
    
    setup_logging(json_config_obj.log_level)

    pull_from_nilrt_details = pull_from_base_branch(json_config_obj.NILRT_branch,"https://github.com/ni/nilrt.git") # To ensure that the NILRT branch is up to date in case files like 'repos.conf' are modified, which would be crucial to the current script
    if pull_from_nilrt_details[0] != 0:
        print(pull_from_nilrt_details[1])
        return
    
    merge_report = merge_submodules_with_upstream(json_config_obj.conf_file, json_config_obj.force_checkout, json_config_obj.username, json_config_obj.upstream_repo_name, json_config_obj.merge_branch_name, json_config_obj.fork_name, skip_merge)

    merge_has_errors = any(status != 0 for status, _ in merge_report.values())

    update_meta_nilrt_branch(json_config_obj.meta_nilrt_branch)

    build_and_test_details = build_and_test(json_config_obj.clean_build, json_config_obj.vm_name, json_config_obj.snapshot_name,merge_has_errors)
    
    merge_report = push_and_PR_prepare(merge_has_errors, build_and_test_details , merge_report ,json_config_obj.merge_branch_name ,json_config_obj.work_item_id, json_config_obj.username)
    merge_report["Build and Test"] = build_and_test_details
    
    write_log_and_send_email(json_config_obj.email_from, json_config_obj.email_to, merge_report, json_config_obj.email_log_level) 
    
if __name__ == "__main__":
    main()
