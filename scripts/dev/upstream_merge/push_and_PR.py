import os

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

def get_PR_description(work_item_id):
    return f"""Merge latest from upstream. No conflicts.
 
    #AB{work_item_id}
    
    - [ ] bitbake packagefeed-ni-core
    - [ ] bitbake packagegroup-ni-desirable
    - [ ] bitbake package-index && bitbake nilrt-base-system-image
    - [ ] Reimaged a cRIO with the new base image and successfully booted it"""