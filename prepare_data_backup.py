import json

from data.backup.conf_backup import Conf
import pandas as pd
import os
from issue import Issue
from commit import *
from pydriller import Repository
from collections import defaultdict


def judge_isconf(file):
    if file["new_path"]:
        path = file["new_path"]
    else:
        path = file["old_path"]
    if "documentation" in path or "xdoc" in path or "zookeeperAdmin" in path:
        return 0
    if str(path).endswith(".xml") or str(path).endswith(".properties"):
        return 1
    return 0

def save_issue(conf, project, issue):
    dir = os.path.join(conf.data_path, "issues", project)
    if os.path.exists(dir):
        file_cnt = len(os.listdir(dir))
        his = json.load(open(os.path.join(dir, str(file_cnt) + ".json"), "r"))
        if len(his) == conf.issue_split_epoch:
            json.dump([issue.to_dict()], open(os.path.join(dir, str(file_cnt + 1) + ".json"), "w"))
        else:
            his.append(issue.to_dict())
            json.dump(his, open(os.path.join(dir, str(file_cnt) + ".json"), "w"))
    else:
        os.mkdir(dir)
        json.dump([issue.to_dict()], open(os.path.join(dir, "1.json"), "w"))
    return


def save_clean(conf, project, clean):
    dir = os.path.join(conf.data_path, "clean", project)
    if os.path.exists(dir):
        file_cnt = len(os.listdir(dir))
        his = json.load(open(os.path.join(dir, str(file_cnt) + ".json"), "r"))
        if len(his) == conf.clean_split_epoch:
            json.dump([clean.to_dict()], open(os.path.join(dir, str(file_cnt + 1) + ".json"), "w"))
        else:
            his.append(clean.to_dict())
            json.dump(his, open(os.path.join(dir, str(file_cnt) + ".json"), "w"))
    else:
        os.mkdir(dir)
        json.dump([clean.to_dict()], open(os.path.join(dir, "1.json"), "w"))
    return


def collect_issue(conf):
    dfs = []
    for year in conf.years:
        df = pd.read_csv(os.path.join(conf.data_path, year + ".csv"))
        dfs.append(df)
    issue_df = pd.concat(dfs, axis=0, ignore_index=True)
    issue_df.drop_duplicates(subset=["Issue key"])
    issue_df['project'] = issue_df["Issue key"].str.split("-").str[0]
    visit_issues = []
    if os.path.exists(os.path.join(conf.data_path, "issues", "visit_issues.json")):
        visit_issues = json.load(open(os.path.join(conf.data_path, "issues", "visit_issues.json"), "r"))
    for project in conf.projects:
        commit_links = pd.read_csv(os.path.join(conf.data_path, "commit_links_" + project + ".csv"))
        issue_fix_links = pd.read_csv(os.path.join(conf.data_path, project + ".csv"))
        for idx, row in issue_df[issue_df["project"] == project].iterrows():
            issue_key = row["Issue key"]
            print(issue_key)
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
                            print(commit.hash)
                            commit_rows = get_commit_row(commit)
                            commit_files, commits_methods = get_files(commit)
                            fix_commit_objs.append(Commit(commit.hash, project, commit_files, commits_methods, commit_rows))
                        for commit in Repository(path_to_repo=os.path.join(conf.repo_path, repo.split("/")[1]),
                                                 only_commits=buggy_commits["bug_hash"].values).traverse_commits():
                            print(commit.hash)
                            commit_rows = get_commit_row(commit)
                            commit_files, commits_methods = get_files(commit)
                            buggy_commit_objs.append(Commit(commit.hash, project, commit_files, commits_methods, commit_rows))
                    issue.set_fix_commits(fix_commit_objs)
                    issue.set_buggy_commits(buggy_commit_objs)
                    save_issue(conf, project, issue)
            visit_issues.append(issue_key)
            json.dump(visit_issues, open(os.path.join(conf.data_path, "issues", "visit_issues.json"), "w"))


def load_issue_from_json(filepath):
    issue_list_json = json.load(open(filepath, "r"))
    issue_list = []
    for issue_json in issue_list_json:
        issue = Issue()
        issue.load_from_dict(issue_json)
        issue_list.append(issue)
    return issue_list


def load_commit_from_json(filepath):
    commit_list_json = json.load(open(filepath, "r"))
    commit_list = []
    for commit_json in commit_list_json:
        commit = Commit()
        commit.load_from_dict(commit_json)
        commit_list.append(commit)
    return commit_list

def filter_conf_issue(conf):
    for project in conf.projects:
        total = 0
        conf_related = 0
        dir = os.path.join(conf.data_path, "issues", project)
        filenames = os.listdir(dir)
        for filename in filenames:
            for issue in load_issue_from_json(os.path.join(dir, filename)):
                print(issue.key)
                total += 1
                if len(issue.fix_commits) > 1:
                    print("more than 1 fix:", issue.key)
                conf_flag = 0
                for fix_commit in issue.fix_commits:
                    for file in fix_commit.files:
                        if judge_isconf(file):
                            conf_flag = 1
                            print("fix:", fix_commit.rows["hash"], "path:", file["new_path"])
                if conf_flag == 1:
                    for buggy_commit in issue.buggy_commits:
                        for file in buggy_commit.files:
                            if judge_isconf(file):
                                print("buggy: ", buggy_commit.rows["hash"], "path:", file["new_path"])
                # desc = str(issue.summary) + str(issue.description)
                # if "config" in desc or "setting" in desc or "param" in desc:
                #     print(issue.key)
                #     print(issue.summary)
                #     print(issue.description)
                #     conf_flag = 1
                if conf_flag == 1:
                    conf_related += 1
        print(total, conf_related)


def collect_clean(conf):
    clean_df = pd.read_csv(os.path.join(conf.data_path, "clean.csv"))
    for project in conf.projects:
        repo = conf.proj_repo[project][0]
        repo_df = clean_df[clean_df["project"] == repo]
        visit_clean = []
        print(project, len(repo_df["commit_id"].values))
        if os.path.exists(os.path.join(conf.data_path, "clean", "visit_cleans.json")):
            visit_clean = json.load(open(os.path.join(conf.data_path, "clean", "visit_cleans.json"), "r"))
        for commit in Repository(path_to_repo=os.path.join(conf.repo_path, repo.split("/")[1]),
                                 only_commits=list(set(repo_df["commit_id"].values) - set(visit_clean))).traverse_commits():
            print(commit.hash)
            commit_rows = get_commit_row(commit)
            commit_files, commits_methods = get_files(commit)
            clean_commit_obj = Commit(commit.hash, project, commit_files, commits_methods, commit_rows)
            save_clean(conf, project, clean_commit_obj)
            visit_clean.append(commit.hash)
            json.dump(visit_clean, open(os.path.join(conf.data_path, "clean", "visit_cleans.json"), "w"))


def filter_conf_clean(conf, filter_project):
    conf_related = []
    type_dict = defaultdict(int)
    for project in conf.projects:
        total = 0
        if project != filter_project:
            continue
        dir = os.path.join(conf.data_path, "clean", project)
        filenames = os.listdir(dir)
        for filename in filenames:
            print(filename)
            for clean_commit in load_commit_from_json(os.path.join(dir, filename)):
                total += 1
                flag = 0
                for file in clean_commit.files:
                    file_type = file["filename"].split(".")[-1]
                    type_dict[file_type] += 1
                    if judge_isconf(file):
                        flag = 1
                    # if (file["old_path"] and ".properties" in file["old_path"]) or (
                    #         file["new_path"] and ".properties" in file["new_path"]):
                    #     print(clean_commit.id)
                    #     if file["old_path"]:
                    #         print(file["old_path"])
                    #     else:
                    #         print(file["new_path"])
                if flag:
                    conf_related.append(clean_commit)
        print("total changes:", total)
        print("conf related changes:", len(conf_related))
        print("type cnt:", str(sorted(type_dict.items(), key=lambda x: x[1])))
    return conf_related


def analyze_clean(conf, conf_clean):
    conf_name_cnt = defaultdict(int)
    conf_total = 0
    for commit in conf_clean:
        if 500 > commit.rows["num_lines_added"] + commit.rows["num_lines_deleted"] >= 200:
            print(commit.id)
        for file in commit.files:
            if judge_isconf(file):
                conf_name_cnt[file["filename"]] += 1
                conf_total += 1
    print("filename", sorted(conf_name_cnt.items(), key=lambda x: x[1], reverse=True))
    print("diverse conf files:", str(len(conf_name_cnt.keys())))
    print("total conf change:", conf_total)


def calculate_chunk(diff_parsed):
    chunk = 0
    keys = ["added", "deleted"]
    for key in keys:
        l = diff_parsed[key]
        init = -1
        for i in l:
            if i[0] != init + 1:
                chunk += 1
            init = i[0]
    return chunk

def analyze_clean_size(conf, conf_clean):
    files = []
    chunks = []
    lines = []
    for commit in conf_clean:
        file_cnt = 0
        chunk_cnt = 0
        line_cnt = 0
        for file in commit.files:
            if judge_isconf(file):
                file_cnt += 1
            line_cnt += (file["num_lines_added"] + file["num_lines_deleted"])
            chunk_cnt += calculate_chunk(file["diff_parsed"])
        files.append(file_cnt)
        chunks.append(chunk_cnt)
        lines.append(line_cnt)
    print("files:", sum(files) / len(files), files[int(len(files) / 2)])
    print("chunks", sum(chunks) / len(chunks), chunks[int(len(chunks) / 2)])
    print("lines", sum(lines) / len(lines), lines[int(len(lines) / 2)])


if __name__ == "__main__":
    conf = Conf()
    # collect_issue(conf)
    # collect_clean(conf)
    for project in conf.projects:
        if project not in ["ZOOKEEPER", "HBASE", "ZEPPELIN"]:
            continue
        conf_clean = filter_conf_clean(conf, project)
        # analyze_clean(conf, conf_clean)
        analyze_clean_size(conf, conf_clean)
    # filter_conf_issue(conf)