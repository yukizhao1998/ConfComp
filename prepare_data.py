from conf import Conf
from config_parser_utils import *
import os
from pydriller import Repository
from commit import *
from prompt import *
import datetime
import pytz
from chatgpt_api_utils import *
import pandas as pd

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


def collect_config_related_change(project, project_path, conf):
    raw_data_dir = os.path.join(conf.data_path, conf.raw_file_name, project)
    if not os.path.exists(raw_data_dir):
        os.mkdir(raw_data_dir)
    if os.path.exists(os.path.join(raw_data_dir, "visited.json")):
        visited = json.load(open(os.path.join(raw_data_dir, "visited.json"), "r"))
    else:
        visited = []
    first = True
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        if commit.hash in visited:
            continue
        # dt = datetime.datetime(1900, 1, 1, 0, 0, 0).replace(tzinfo=pytz.timezone('UTC'))
        # if commit.author_date < dt:
        #     print("error! date")
        # dt = commit.author_date
        if first:
            first = False
            continue
        # if commit.hash != "728c4fa9bf2b2c11dbc61c8e5536b1542abc1ccb":
        # #if commit.hash != "9c953d1ae260f062f696dad48ed40e68b78af2ba":
        #     continue
        print(commit.hash)
        commit_chunks = {"code_change_chunks": [], "config_change_chunks": []}
        commit_rows = get_commit_row(commit)
        commit_files, commits_methods = get_files(commit)
        for file in commit_files:
            is_config = False
            for suffix in conf.config_file_suffix:
                if file["filename"].endswith(suffix):
                    commit_chunks["config_change_chunks"].append({"old_path": file["old_path"],
                                                                "new_path": file["new_path"],
                                                                "chunks": merge_chunk(file["diff_parsed"])})
                    is_config = True
                    break
            if not is_config and file["filename"].endswith(".java"):
                commit_chunks["code_change_chunks"].append({"old_path": file["old_path"],
                                                            "new_path": file["new_path"],
                                                            "chunks": merge_chunk(file["diff_parsed"])})
        if len(commit_chunks["code_change_chunks"]) > 0 and len(commit_chunks["config_change_chunks"]) > 0:
            json.dump(commit_chunks, open(os.path.join(raw_data_dir, commit.hash + ".json"), "w"))
        visited.append(commit.hash)
        json.dump(visited, open(os.path.join(raw_data_dir, "visited.json"), "w"))


def generate_label(project, project_path, conf):
    if os.path.exists(os.path.join(conf.data_path, conf.raw_file_name, project)):
        file_list = os.listdir(os.path.join(conf.data_path, conf.raw_file_name, project))
        if "visited.json" in file_list:
            file_list.remove("visited.json")
    else:
        return
    if os.path.exists(os.path.join(conf.data_path, "label.csv")):
        df = pd.read_csv(os.path.join(conf.data_path, "label.csv"))
    else:
        df = pd.DataFrame({"project": [], "commit_hash": [], "code_change_old_path": [], "code_change_new_path": [],
                           "config_change_old_path": [], "config_change_new_path": [], "label": []})
    total_word = 0
    for file in file_list:
        commit_hash = file.strip(".json")
        # if commit_hash != "728c4fa9bf2b2c11dbc61c8e5536b1542abc1ccb":
        # #if commit_hash != "9c953d1ae260f062f696dad48ed40e68b78af2ba":
        #     continue
        commit_chunks = json.load(open(os.path.join(conf.data_path, conf.raw_file_name, project, file), "r"))
        for code_change in commit_chunks["code_change_chunks"]:
            for config_change in commit_chunks["config_change_chunks"]:
                if len(df[(df["commit_hash"] == commit_hash) & (df["code_change_old_path"] == code_change["old_path"])
                       & (df["code_change_new_path"] == code_change["new_path"])
                       & (df["config_change_old_path"] == config_change["old_path"])
                       & (df["config_change_new_path"] == config_change["new_path"])]) > 0:
                    continue
                # if code_change["old_path"] and code_change["new_path"] and code_change["old_path"] != code_change["new_path"]:
                #     sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                #                        "chunks": []}
                #     prompt = label_query_prompt(sub_code_change, config_change)
                #     print("*********************************************************")
                #     for subprompt in prompt:
                #         print(subprompt)
                #     # response = call_chatgpt_api(prompt)
                #     # answer = response["choices"][0]["message"]["content"]
                #     # print(answer)
                for code_change_chunk in code_change["chunks"]:
                    sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                                       "chunks": [code_change_chunk]}
                    prompt = label_query_prompt(sub_code_change, config_change)
                    for subprompt in prompt:
                        total_word += len(subprompt.split(" "))
                    # print("*********************************************************")
                    # for subprompt in prompt:
                    #     print(subprompt)
                    # response = call_chatgpt_api(prompt)
                    # answer = response["choices"][0]["message"]["content"]
                    # print(answer)
                # new_row = pd.DataFrame({"project": [project], "commit_hash": [commit_hash], "code_change_old_path": [code_change["old_path"]],
                #            "code_change_new_path": [code_change["new_path"]], "config_change_old_path": [config_change["old_path"]],
                #            "config_change_new_path": [config_change["new_path"]], "label": [answer]})
                # df = pd.concat([df, new_row])
                # df.to_csv(os.path.join(conf.data_path, "label.csv"), index=False)


def count_project_commits(project, project_path, conf):
    cnt = 0
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        cnt += 1
    print(cnt)

if __name__ == "__main__":
    conf = Conf()
    # print(call_chatgpt_api("who are you?"))
    # collect raw chunks
    # print(call_chatgpt_api(["Here is a piece of text.\nI am Joe Brown. I work in Peking University as a professor.",
    #                   "By considering the above text, answer the questions: Who am I?",
    #                   "By considering the above text, answer the questions: Where do I work?"]))
    # count commits
    # for project in conf.projects:
    #     project_path = os.path.join(conf.repo_path, project)
    #     if os.path.exists(project_path):
    #         print(project_path)
    #         count_project_commits(project, project_path, conf)
    # collect chunks
    if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name)):
        os.mkdir(os.path.join(conf.data_path, conf.raw_file_name))
    # for project in conf.projects:
    #     project_path = os.path.join(conf.repo_path, project)
    #     if os.path.exists(project_path):
    #         print(project_path)
    #         # if not project == "rocketmq":
    #         #     continue
    #         collect_config_related_change(project, project_path, conf)
    # label chunks
    for project in conf.projects:
        if not project in ["dubbo", "kafka", "roketmq"]:
            continue
        project_path = os.path.join(conf.repo_path, project)
        if os.path.exists(project_path):
            print(project_path)
            generate_label(project, project_path, conf)