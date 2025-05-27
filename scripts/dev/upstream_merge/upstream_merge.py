import os
from GitRepo import *

def merge_submodules_with_upstream(conf_file, force_checkout, username, upstream_repo_name, merge_branch_name, fork_name, skip_merge):
    merge_report = {}
    current_directory = os.getcwd()

    with open(conf_file, "r") as file: # Read the configuration file - `repos.conf` and not the `automation_conf.json`
        for line in file:
            if line.startswith("#"):
                continue
            parts = line.split()
            token = os.environ["GH_PAT"]
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

def merge_upstream(git_obj,force_checkout, merge_branch_name, skip_merge):
    if skip_merge == "True":
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

