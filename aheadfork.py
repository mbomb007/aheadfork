#!/usr/bin/python3
# -*-coding:utf-8-*-
"""
Find all fork repo that are ahead of original repo
Before running, install requirement first: python3 -m pip install requests

Reference: https://docs.github.com/en/free-pro-team@latest/rest/reference
"""
import sys
import json
import time
import requests
import getpass
from math import ceil

GITHUB_API_TOKEN = ""
REPO = ""
DEBUG = True

def get_forks():
    session = requests.Session()
    forks = []

    # auth
    auth_url = "https://api.github.com"
    session.headers.update({'Authorization': 'token ' + GITHUB_API_TOKEN})  # should carry this header for all request
    resp = session.get(auth_url)
    if resp.status_code != 200:
        resp_json = resp.json()
        msg = resp_json.get('message')
        print('[-] Auth error: %s' % msg)
        return []
    if DEBUG:
        print("[*] Github API Rate Limit. Limit: %s, Remaining: %s, Reset: %s" % (
            resp.headers.get("X-RateLimit-Limit"),
            resp.headers.get("X-RateLimit-Remaining"),
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(resp.headers.get("X-RateLimit-Reset"))))
        ))

    # set header
    session.headers.update({'Accept': 'application/vnd.github.v3+json'})

    # get repo info
    repo_url = "https://api.github.com/repos/%s" % REPO
    resp = session.get(repo_url)
    if resp.status_code != 200:
        print("[-] Get repo info failed: %s" % resp.text)
        return []
    forks_count = json.loads(resp.text).get("forks")
            
    # determine branches of repo likely to be the primary branch
    branches_url = "https://api.github.com/repos/%s/branches"
    branches = session.get(branches_url % REPO, headers={'Accept': 'application/vnd.github.v3+json'}).json()
    primary_branch_options = []
    for branch in branches:
        branch_name = branch.get("name")
        if branch_name == "master" or branch_name == "main" or branch.get("protected"):
            primary_branch_options.append(branch_name)
    
    # ask user to choose branch if cannot infer primary branch
    if len(primary_branch_options) == 0:
        print('Could not determine primary branch for repo.')
        branch_names = str([branch.get("name") for branch in branches])
        primary_branch = input('Please enter the name of the primary branch. Branch list: \n%s\n' % branch_names)
        if primary_branch not in branch_names:
            print('Invalid branch name.')
            exit(1)
    elif len(primary_branch_options) > 1:
        print('Could not determine primary branch for repo. %n options found.')
        branch_names = str(primary_branch_options)
        primary_branch = input('Please enter the name of the primary branch. Branch list: \n%s\n' % branch_names)
        if primary_branch not in branch_names:
            # see if a valid branch that wasn't a likely candidate was entered
            for branch in branches:
                if branch.get('name') == primary_branch:
                    break;
            else:
                print('Invalid branch name.')
                exit(1)
    else:
         primary_branch = primary_branch_options[0]

    # get forks
    page_count = ceil(forks_count / 30)  # 30 items each page
    for page in range(1, page_count + 1):
        params = {"page": page}
        forks_url = "https://api.github.com/repos/%s/forks" % REPO
        resp = session.get(forks_url, params=params, headers={'Accept': 'application/vnd.github.v3+json'})
        if resp.status_code != 200:
            print('[-] Get forks failed: %s' % resp.text)
            return []

        repos = json.loads(resp.text)
        for repo in repos:
            if DEBUG:
                print("[*] get fork: " + repo.get("full_name"))
            forks.append({
                "full_name": repo.get("full_name"),
                "pushed_at": repo.get("pushed_at"),
                "stargazers_count": repo.get("stargazers_count"),
                "forks_count": repo.get("forks_count")
            })

    # compare (ONLY compare primary branch)
    compare_branches = "%s...%s" % (primary_branch, primary_branch)
    compare_url = "https://api.github.com/repos/%s/compare/%s:" + compare_branches
    for fork in forks:
        if DEBUG:
            print("[*] compare %s" % fork.get("full_name"))
        resp = session.get(compare_url % (fork.get("full_name"), REPO.split("/")[0]), headers={'Accept': 'application/vnd.github.v3+json'})
        if resp.status_code != 200:
            print('[-] compare %s failed: %s' % (fork.get("full_name"), resp.text))
            continue
        res = json.loads(resp.text)
        fork.update({
            "ahead_by": res.get("ahead_by"),
            "behind_by": res.get("behind_by")
        })

    return forks

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        GITHUB_API_TOKEN = sys.argv[1].strip()
        REPO = sys.argv[2].strip()
    elif len(sys.argv) == 2:
        GITHUB_API_TOKEN = getpass.getpass(prompt="GitHub API Token: ")
        REPO = sys.argv[1].strip()
    else:
        print("Usage 1: python3 %s GITHUB_API_TOKEN REPO" % sys.argv[0])
        print("\teg: python3 %s ab124942710137429ffdac322314701471234411 Ovi3/BurpBeautifier" % sys.argv[0])
        
        print("Usage 2: python3 %s REPO" % sys.argv[0])
        print("\teg: python3 %s Ovi3/BurpBeautifier (will prompt for API key)" % sys.argv[0])
        exit(0)

    try:
        forks = get_forks()
        if forks:
            # only show fork that is ahead of original repo. sorted by ahead_by and pushed_at
            forks = list(filter(lambda i: i.get("ahead_by"), forks))
            forks = sorted(forks, key=lambda i: (i.get("ahead_by"), i.get("pushed_at")), reverse=True)

            print("Done")
            print("%-48s%-30s%-8s%-8s%-8s%-8s" % ("name", "last push", "star", "fork", "ahead", "behind"))
            for fork in forks:
                print("%-48s%-30s%-8d%-8d%-8d%-8d" % (
                    fork.get("full_name"),
                    fork.get("pushed_at"),
                    fork.get("stargazers_count"),
                    fork.get("forks_count"),
                    fork.get("ahead_by"),
                    fork.get("behind_by"),
                ))
    except Exception as e:
        print("[-] Error: %s" % e.args)

