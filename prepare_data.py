from conf import Conf
from config_parser_utils import *
import os
from pydriller import Repository
from commit import *
from prompt import *

def merge_chunk(diff_parsed):
    diff_parsed_clone = {"added": [], "deleted": []}
    for key in diff_parsed:
        for item in diff_parsed[key]:
            diff_parsed_clone[key].append([item[0], item[1]])
    lines = []
    dlen = len(diff_parsed["deleted"])
    alen = len(diff_parsed["added"])
    idx = 1
    didx = 0
    aidx = 0
    while True:
        if didx >= dlen and aidx >= alen:
            break
        if didx < dlen and idx == diff_parsed_clone["deleted"][didx][0]:
            for i in range(aidx, alen):
                diff_parsed_clone["added"][i][0] += 1
            lines.append(-1)
            didx += 1
        elif aidx < alen and idx == diff_parsed_clone["added"][aidx][0]:
            for i in range(didx, dlen):
                diff_parsed_clone["deleted"][i][0] += 1
            lines.append(1)
            aidx += 1
        else:
            lines.append(0)
        idx += 1
    chunks = []
    p = 0
    dp = 0
    ap = 0
    while p < len(lines):
        if lines[p] == 0:
            p += 1
            continue
        else:
            chunk = {"deleted": [], "added": []}
            while p < len(lines):
                if lines[p] == -1:
                    chunk["deleted"].append(diff_parsed["deleted"][dp])
                    dp += 1
                    p += 1
                elif lines[p] == 1:
                    chunk["added"].append(diff_parsed["added"][ap])
                    ap += 1
                    p += 1
                else:
                    break
            chunks.append(chunk)
    return chunks


def collect_config_related_change(project_path, conf):
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        if commit.hash != "728c4fa9bf2b2c11dbc61c8e5536b1542abc1ccb":
            continue
        print(commit.hash)
        commit_rows = get_commit_row(commit)
        commit_files, commits_methods = get_files(commit)
        config_file_list = []
        java_file_list = []
        for file in commit_files:
            if file["filename"] == "Scrubber.java":
                print(file["diff_parsed"])
                print(chunk_prompt(merge_chunk(file["diff_parsed"])))
            is_config = False
            for suffix in conf.config_file_suffix:
                if file["filename"].endswith(suffix):
                    config_file_list.append(file["filename"])
                    is_config = True
                    break
            if not is_config and file["filename"].endswith(".java"):
                java_file_list.append(file["filename"])

        if len(config_file_list) and len(java_file_list):
            print("found!")
            print(config_file_list)
            print(java_file_list)



if __name__ == "__main__":
    conf = Conf()
    for project in conf.projects:
        project_path = os.path.join(conf.repo_path, project)
        if os.path.exists(project_path):
            print(project_path)
            collect_config_related_change(project_path, conf)