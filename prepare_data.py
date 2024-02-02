import os
from pydriller import Repository
from commit import *
from prompt import *
from chatgpt_api_utils import *
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tqdm import tqdm
import argparse


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


def get_gpt_response(prompt, config_change, code_change_old_path, code_change_new_path, config_change_old_path,
                     config_change_new_path, conf):
    res = {"code_change_old_path": code_change_old_path, "code_change_new_path": code_change_new_path,
           "config_change_old_path": config_change_old_path, "config_change_new_path": config_change_new_path,
           "result": "{}"}
    try:
        response = call_chatgpt_api(prompt, conf)
        messages = list()
        messages.append({"role": "assistant", "content": response["choices"][0]["message"]["content"]})
        _, response = call_chatgpt_api_multi(messages, [format_prompt(len(config_change["chunks"]))], conf)
        res = {"code_change_old_path": code_change_old_path, "code_change_new_path": code_change_new_path,
                "config_change_old_path": config_change_old_path, "config_change_new_path": config_change_new_path,
                "result": response["choices"][0]["message"]["content"]}
        # time.sleep(5)
    except Exception as e:
        print(e)
        print("Exception when getting gpt result: " + json.dumps(code_change_new_path))
    return res


def get_modify_size(file):
    content_tokens = 0
    chunk_cnt = 0
    enc = get_label_tokenizer()
    for chunk in file["chunks"]:
        chunk_cnt += 1
        for key in chunk:
            content_tokens += len(enc.encode("\n".join([item[1] for item in chunk[key]])))
    return chunk_cnt, content_tokens


def get_file_cnt_bar(project_path, conf):
    code_file_cnt = []
    config_file_cnt = []
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        commit_hash = commit.hash
        if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json")):
            continue
        if commit.author_date < conf.dt_start or commit.author_date > conf.dt_end:
            continue
        commit_chunks = json.load(open(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json"), "r"))
        code_file_cnt.append(len(commit_chunks["code_change_chunks"]))
        config_file_cnt.append(len(commit_chunks["config_change_chunks"]))
    code_file_cnt.sort()
    config_file_cnt.sort()
    for i in range(1, 11):
        print("i", i * 0.1)
        print("code", code_file_cnt[int(len(code_file_cnt) * i * 0.1) - 1])
    return code_file_cnt[int(len(code_file_cnt) * conf.file_cnt_bar_prop) - 1], config_file_cnt[int(len(config_file_cnt) * conf.file_cnt_bar_prop) - 1]


def exist_config_file(commit_chunks, conf):
    for chunk in commit_chunks["config_change_chunks"]:
        for suffix in conf.config_file_suffix:
            if (chunk["old_path"] and chunk["old_path"].endswith(suffix)) or (chunk["new_path"] and chunk["new_path"].endswith(suffix)):
                return True
    return False



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
    commit_cnt = 0
    commit_cnt_before = 0
    # code_file_bar, config_file_bar = get_file_cnt_bar(project_path, conf)
    # print("bar", code_file_bar, config_file_bar)
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        commit_hash = commit.hash
        if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json")):
            continue
        if commit.author_date < conf.dt_start or commit.author_date > conf.dt_end:
            continue
        commit_chunks = json.load(open(os.path.join(conf.data_path, conf.raw_file_name, project, commit_hash + ".json"), "r"))
        if not exist_config_file(commit_chunks, conf):
            continue
        commit_cnt_before += 1
        if len(commit_chunks["code_change_chunks"]) > conf.code_file_cnt_bar:
            continue
        commit_cnt += 1
        total_res = []
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for code_change in commit_chunks["code_change_chunks"]:
                for config_change in commit_chunks["config_change_chunks"]:
                    # code_chunk_cnt, code_modify_tokens = get_modify_size(code_change)
                    # print(code_chunk_cnt, code_modify_tokens)
                    if len(df[(df["commit_hash"] == commit_hash) & (df["code_change_old_path"] == str(code_change["old_path"]))
                              & (df["code_change_new_path"] == str(code_change["new_path"]))
                              & (df["config_change_old_path"] == str(config_change["old_path"]))
                              & (df["config_change_new_path"] == str(config_change["new_path"]))]) > 0:
                        continue

                    total_res.append({"code_change_old_path": str(code_change["old_path"]),
                                      "code_change_new_path": str(code_change["new_path"]),
                                      "config_change_old_path": str(config_change["old_path"]),
                                      "config_change_new_path": str(config_change["new_path"]),
                                      "result": {}})
                    for i in range(len(config_change["chunks"])):
                        total_res[-1]["result"]["chunk " + str(i + 1)] = 0
                    sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                                       "chunks": []}
                    for i, code_change_chunk in enumerate(code_change["chunks"]):
                        sub_code_change["chunks"].append(code_change_chunk)
                        prompt = label_query_prompt(sub_code_change, config_change)
                        token_cnt = len(enc.encode("\n".join(prompt)))
                        if len(sub_code_change["chunks"]) > 3 or token_cnt > 1000 or i == len(code_change["chunks"]) - 1:
                            futures.append(executor.submit(get_gpt_response, prompt, config_change, str(code_change["old_path"]),
                                                             str(code_change["new_path"]), str(config_change["old_path"]),
                                                             str(config_change["new_path"]), conf))
                            sub_code_change = {"old_path": code_change["old_path"], "new_path": code_change["new_path"],
                                               "chunks": []}
            if len(futures) > 0:
                print(commit_hash)
            # wait(futures, return_when=ALL_COMPLETED)
            # for future in futures:
            for future in tqdm(as_completed(futures), total=len(futures)):
                res = future.result()
                for idx, ele in enumerate(total_res):
                    if ele["code_change_old_path"] == res["code_change_old_path"] and \
                            ele["code_change_new_path"] == res["code_change_new_path"] and \
                            ele["config_change_old_path"] == res["config_change_old_path"] and \
                            ele["config_change_new_path"] == res["config_change_new_path"]:
                        ele["result"] = merge_result(ele["result"], res["result"])
                        total_res[idx] = ele
            for line in total_res:
                df.loc[len(df)] = [project, commit_hash, line["code_change_old_path"], line["code_change_new_path"],
                                   line["config_change_old_path"], line["config_change_new_path"], json.dumps(line["result"])]
                df.to_csv(os.path.join(conf.data_path, "label.csv"), index=False)
    # print("Summary for " + project)
    print(commit_cnt_before, commit_cnt, commit_cnt / commit_cnt_before)
    # print("total commit:", commit_cnt)
    # print("total prompt:", prompt_cnt)
    # print("total token:", total_token_cnt)
    # word_distribute = sorted(word_distribute)
    # for i in range(10):
    #     idx = min(len(word_distribute) - 1, int(len(word_distribute) * 0.1 * (i + 1) - 1))
    #     print(0.1 * (i + 1), word_distribute[idx])


def count_project_commits(project, project_path, conf):
    cnt = 0
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        if commit.author_date < conf.dt_start or commit.author_date > conf.dt_end:
            continue
        cnt += 1
    print(project, cnt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai_api_key", "-o", help="openai_api_key")
    args = parser.parse_args()

    conf = Conf()
    conf.openai_api_key = args.openai_api_key

    if not os.path.exists(conf.data_path):
        os.mkdir(conf.data_path)
    for project in conf.projects:
        project_path = os.path.join(conf.repo_path, project)
        count_project_commits(project, project_path, conf)
    # collect chunks
    if not os.path.exists(os.path.join(conf.data_path, conf.raw_file_name)):
        os.mkdir(os.path.join(conf.data_path, conf.raw_file_name))
    for project in conf.projects:
        project_path = os.path.join(conf.repo_path, project)
        if os.path.exists(project_path):
            print("collecting chunks for " + project_path)
            collect_config_related_change(project, project_path, conf)
    #
    # # label_chunks
    # for project in conf.projects:
    #     project_path = os.path.join(conf.repo_path, project)
    #     if os.path.exists(project_path):
    #         print("labeling chunks for " + project_path)
    #         label_chunks(project, project_path, conf)