import json
import uuid

from conf import Conf
import pandas as pd
import os
from issue import Issue
from commit import *
from pydriller import Repository, Git


def load_issue(conf):
    dfs = []
    for year in conf.years:
        df = pd.read_csv(os.path.join(conf.data_path, year + ".csv"))
        dfs.append(df)
    issue_df = pd.concat(dfs, axis=0, ignore_index=True)
    issue_df.drop_duplicates(subset=["Issue key"])
    issue_df['project'] = issue_df["Issue key"].str.split("-").str[0]
    issues = []
    visit_issues = []
    if os.path.exists(os.path.join(conf.data_path, "issues.json")) and os.path.exists(os.path.join(conf.data_path, "visit_issues.json")):
        issues = json.load(open(os.path.join(conf.data_path, "issues.json"), "r"))
        visit_issues = json.load(open(os.path.join(conf.data_path, "visit_issues.json"), "r"))


    for project in conf.projects:
        commit_links = pd.read_csv(os.path.join(conf.data_path, "commit_links_" + project + ".csv"))
        issue_fix_links = pd.read_csv(os.path.join(conf.data_path, project + ".csv"))
        for idx, row in issue_df[issue_df["project"] == project].iterrows():
            issue_key = row["Issue key"]
            if issue_key in visit_issues:
                continue
            fix_commits = issue_fix_links[issue_fix_links["issue_key"] == issue_key]
            if fix_commits.size != 0:
                buggy_commits = commit_links[commit_links["fix_hash"].isin(fix_commits["commit_id"])]
                if buggy_commits.size != 0:
                    issue = Issue(row["Issue key"], row["Issue id"], row["Summary"], row["Description"], row["Priority"],
                                  row["Created"], row["Updated"])
                    fix_commit_objs = []
                    buggy_commit_objs = []
                    for repo in conf.proj_repo[project]:
                        for commit in Repository(path_to_repo=os.path.join(conf.repo_path, repo.split("/")[1]),
                                                 only_commits=fix_commits["commit_id"].values).traverse_commits():
                            commit_rows = get_commit_row(commit)
                            commit_files, commits_methods = get_files(commit)
                            fix_commit_objs.append(Commit(commit.hash, project, commit_files, commits_methods, commit_rows))
                        for commit in Repository(path_to_repo=os.path.join(conf.repo_path, repo.split("/")[1]),
                                                 only_commits=buggy_commits["bug_hash"].values).traverse_commits():
                            commit_rows = get_commit_row(commit)
                            commit_files, commits_methods = get_files(commit)
                            buggy_commit_objs.append(Commit(commit.hash, project, commit_files, commits_methods, commit_rows))
                    issue.set_fix_commits(fix_commit_objs)
                    issue.set_buggy_commits(buggy_commit_objs)
                    for commit in fix_commit_objs:
                        print(commit.__dict__)
                    print(issue.__dict__)
                    issues.append(issue.to_dict())
                    json.dump(issues, open(os.path.join(conf.data_path, "issues.json"), "w"))
            visit_issues.append(issue_key)
            json.dump(visit_issues, open(os.path.join(conf.data_path, "visit_issues.json"), "w"))


def filter_conf():
    pass

if __name__ == "__main__":
    conf = Conf()
    load_issue(conf)
    filter_conf()