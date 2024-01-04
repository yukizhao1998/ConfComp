import os
from pydriller import Repository
from commit import *
from prompt import *
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
        if first:
            first = False
            continue
        if commit.hash in visited:
            continue
        print(commit.hash)
        commit_chunks = {"code_change_chunks": [], "config_change_chunks": []}
        # commit_rows = get_commit_row(commit)
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


def merge_result(result, response_json):
    try:
        response_json = json.loads(response_json)
        if len(result.keys()) != len(response_json.keys()):
            raise ValueError("Invalid keys for response!")
        for key in result.keys():
            if key not in response_json:
                raise ValueError("Invalid keys for response!")
            if response_json[key] != 0 and response_json[key] != 1:
                raise ValueError("Invalid value for response!")
        for key in result.keys():
            result[key] = max(result[key], response_json[key])
    except Exception as e:
        print(e)
        print("Exception when parsing labeling result: " + json.dumps(response_json))
    return result


def label_chunks(project, project_path, conf):
    enc = get_label_tokenizer()
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
    total_token_cnt = 0
    prompt_cnt = 0
    commit_cnt = 0
    word_distribute = []
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        commit_hash = commit.hash
        if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json")):
            continue
        if commit.author_date < conf.dt_start or commit.author_date > conf.dt_end:
            continue
        commit_cnt += 1
        commit_chunks = json.load(open(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json"), "r"))
        print_cnt = 0
        for code_change in commit_chunks["code_change_chunks"]:
            for config_change in commit_chunks["config_change_chunks"]:
                if len(df[(df["commit_hash"] == commit_hash) & (df["code_change_old_path"] == str(code_change["old_path"]))
                          & (df["code_change_new_path"] == str(code_change["new_path"]))
                          & (df["config_change_old_path"] == str(config_change["old_path"]))
                          & (df["config_change_new_path"] == str(config_change["new_path"]))]) > 0:
                    continue
                result = {}
                for i in range(len(config_change["chunks"])):
                    result["chunk " + str(i + 1)] = 0
                sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                                   "chunks": []}
                for i, code_change_chunk in enumerate(code_change["chunks"]):
                    # if all the chunks of the config is labeled as related, break
                    flag = True
                    for key in result:
                        if result[key] == 0:
                            flag = False
                    if flag:
                        break
                    sub_code_change["chunks"].append(code_change_chunk)
                    prompt = label_query_prompt(sub_code_change, config_change)
                    token_cnt = len(enc.encode("\n".join(prompt)))
                    if len(sub_code_change["chunks"]) > 3 or token_cnt > 1000 or i == len(code_change["chunks"]) - 1:
                        response = call_chatgpt_api(prompt)
                        messages = list()
                        messages.append({"role": "assistant", "content": response["choices"][0]["message"]["content"]})
                        _, response = call_chatgpt_api_multi(messages, [format_prompt(len(config_change["chunks"]))])
                        result = merge_result(result, response["choices"][0]["message"]["content"])
                        total_token_cnt += token_cnt
                        prompt_cnt += 1
                        word_distribute.append(token_cnt)
                        sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                                           "chunks": []}
                df.loc[len(df)] = [project, commit_hash, str(code_change["old_path"]), str(code_change["new_path"]), str(config_change["old_path"]),
                                   str(config_change["new_path"]), json.dumps(result)]
                df.to_csv(os.path.join(conf.data_path, "label.csv"), index=False)
    print("Summary for " + project)
    print("total commit:", commit_cnt)
    print("total prompt:", prompt_cnt)
    print("total token:", total_token_cnt)
    word_distribute = sorted(word_distribute)
    for i in range(10):
        idx = min(len(word_distribute) - 1, int(len(word_distribute) * 0.1 * (i + 1) - 1))
        print(0.1 * (i + 1), word_distribute[idx])


def count_project_commits(project, project_path, conf):
    cnt = 0
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        cnt += 1
    print(cnt)


if __name__ == "__main__":
    conf = Conf()
    if not os.path.exists(conf.data_path):
        os.mkdir(conf.data_path)
    # collect chunks
    if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name)):
        os.mkdir(os.path.join(conf.data_path, conf.raw_file_name))
    for project in conf.projects:
        project_path = os.path.join(conf.repo_path, project)
        if os.path.exists(project_path):
            print("collecting chunks for " + project_path)
            collect_config_related_change(project, project_path, conf)
    # label_chunks
    # for project in conf.projects:
    #     project_path = os.path.join(conf.repo_path, project)
    #     if os.path.exists(project_path):
    #         print("labeling chunks for " + project_path)
    #         label_chunks(project, project_path, conf)