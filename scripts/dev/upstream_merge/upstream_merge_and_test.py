import datetime
import os
import argparse
import logging
from json_config import json_config
from GitRepo import *
from git_commands import send_email
from build import build_images
from test import OS_test

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

def switch_to_base_branch_and_pull(git_obj,force_checkout):
    if not force_checkout:
        branch_details = git_obj.branch_exists(git_obj.local_base_branch)
        if not branch_details:
            print(f"\n    Branch {git_obj.local_base_branch} does not exist. Exiting")
            return (1,f"\n    Branch {git_obj.local_base_branch} does not exist. Exiting")
    
    checkout_details = git_obj.checkout_branch(git_obj.local_base_branch,force_checkout=force_checkout)
    if checkout_details[0] != 0:
        print(checkout_details[1])
        return checkout_details
    
    set_origin_details = git_obj.add_remote("origin",f"https://github.com/ni/" + git_obj.local_repo.split("/")[1] + ".git")
    if set_origin_details[0] != 0:
        print(set_origin_details[1])
        return set_origin_details
    
    pull_latest_details = git_obj.pull_latest(branch_name=git_obj.local_base_branch,upstream_repo_name="origin")
    if pull_latest_details[0] != 0:
        print(pull_latest_details[1])
        return pull_latest_details

    return (0,None)
    
def fetch_upstream(git_obj):
    add_remote_details = git_obj.add_remote()
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details
    
    fetch_details = git_obj.fetch_branch()
    if fetch_details[0] != 0:
        print(fetch_details[1])
        return fetch_details

    return (0,None)

def create_merge_branch(git_obj,merge_branch_name):
    if git_obj.branch_exists(merge_branch_name):
        git_obj.checkout_branch(git_obj.local_base_branch)
        git_obj.delete_branch(merge_branch_name)

    checkout_details = git_obj.checkout_branch(merge_branch_name,create=True)
    if checkout_details[0] != 0:
        print(checkout_details[1])
        return checkout_details
    
    return (0,None)

def prepare_for_merge(git_obj, merge_branch_name, force_checkout):
    print(f"{git_obj.local_repo}")

    base_branch_details = switch_to_base_branch_and_pull(git_obj,force_checkout)
    if base_branch_details[0] != 0:
        return base_branch_details
    
    fetch_details = fetch_upstream(git_obj)
    
    if fetch_details[0] != 0:
        return fetch_details
    
    repo_details = create_merge_branch(git_obj, merge_branch_name)

    if repo_details[0] != 0:
        return repo_details
    
    return (0,None)

def merge_upstream(git_obj,force_checkout, merge_branch_name, skip_merge):
    if skip_merge == "True" or skip_merge == "true":
        return (0," Has Been Skipped")
    print(f"{git_obj.local_repo}\n")

    merge_prepare_details = prepare_for_merge(git_obj,merge_branch_name,force_checkout)
    
    if merge_prepare_details[0] != 0:
        return merge_prepare_details
    
    commit_before_merge = git_obj.get_current_commit()
    
    merge_result = git_obj.merge_branch(f"{git_obj.upstream_repo_name}/{git_obj.upstream_branch}", "Merge latest upstream")

    if merge_result[0] == 0:        
        diff_output=git_obj.diff()    
        if (git_obj.get_current_commit() == commit_before_merge) or diff_output == (0,''):
            return (0,None)
        else:
            return (0,diff_output[1])
    else:
        return (1,merge_result[1])

def push_branch_and_create_PR(git_obj, merge_branch_name, work_item_id, username):
    push_details = push_branch(git_obj,merge_branch_name)
    if push_details[0] != 0:
        print(push_details[1])
        return push_details
    
    # PR_details = create_PR(git_obj,merge_branch_name,work_item_id,username)
    # if PR_details[0] !=0:
    #     print(PR_details[1])
    #     return PR_details

    return (0,None)

def push_branch(git_obj,merge_branch_name):
    add_remote_details = git_obj.add_remote(git_obj.fork_name, git_obj.fork_url)
    if add_remote_details[0] != 0:
        print(add_remote_details[1])
        return add_remote_details
    
    if git_obj.branch_exists(merge_branch_name,git_obj.fork_name,check_on_remote=True):
        push_delete_details = git_obj.push(merge_branch_name, git_obj.fork_name, delete=True)
        if push_delete_details[0] != 0:
            print(push_delete_details[1])
            return push_delete_details
    
    push_derails = git_obj.push(merge_branch_name, git_obj.fork_name)
    if push_derails[0] != 0:
        print(push_derails[1])
        return push_derails
    
    return (0,None)

def create_PR(git_obj, merge_branch_name, work_item_id, username):
    PR_details = git_obj.create_pull_request("Automated Merge PR",get_PR_description(work_item_id),git_obj.local_base_branch,f"{username}:{merge_branch_name}")
    if PR_details[0] != 0:
        print(PR_details[1])
        return PR_details
    
    return (0,None)
    
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

def merge_submodules_with_upstream(conf_file, force_checkout, username, upstream_repo_name, merge_branch_name, fork_name, skip_merge):
    merge_report = {}
    current_directory = os.getcwd()

    with open(conf_file, "r") as file: # Read the configuration file - `repos.conf` and not the `automation_conf.json`
        for line in file:
            if line.startswith("#"):
                continue
            parts = line.split()
            token = os.environ.get("GH_PAT")
            if token is None:
                fork_url = f"https://github.com/{username}/" + parts[0].split("/")[1] + ".git"
            else:
                fork_url = f"https://x-access-token:{token}@github.com/{username}/" + parts[0].split("/")[1] + ".git"
            git_obj=GitRepo(local_repo=parts[0],
                            upstream_repo_url=parts[1],
                            upstream_branch=parts[2],
                            local_base_branch=parts[3],
                            upstream_repo_name=upstream_repo_name,
                            fork_name=fork_name,
                            fork_url=fork_url)
            os.chdir(git_obj.local_repo)
            merge_report[git_obj] = merge_upstream(git_obj, force_checkout, merge_branch_name, skip_merge)
            os.chdir(current_directory)
    return merge_report

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

def push_and_PR_prepare(merge_has_errors, build_and_test_details, merge_report, merge_branch_name, work_item_id, username):
    if merge_has_errors == False:
        push_and_PR_results = {}
        if build_and_test_details[0] == 0:
            for git_obj, (status, message) in list(merge_report.items()):
                if status == 0 and message is not None:
                    current_directory = os.getcwd()
                    os.chdir(git_obj.local_repo)
                    push_and_PR_results[git_obj] = push_branch_and_create_PR(git_obj, merge_branch_name, work_item_id, username)
                    os.chdir(current_directory)

            merge_report["Push and PR"] = push_and_PR_results

    return merge_report

def get_PR_description(work_item_id):
    return f"""Merge latest from upstream. No conflicts.
 
    #AB{work_item_id}
    
    - [ ] bitbake packagefeed-ni-core
    - [ ] bitbake packagegroup-ni-desirable
    - [ ] bitbake package-index && bitbake nilrt-base-system-image
    - [ ] Reimaged a cRIO with the new base image and successfully booted it"""

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
    config_file_path = args.c

    json_config_obj = json_config(config_file_path,workitemID=args.w)    
    
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
