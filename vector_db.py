import json
import os
from pinecone import Pinecone, ServerlessSpec
from pydriller import Git, Repository
import pandas as pd
from chatgpt_api_utils import *
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from multiprocessing import Pool
import time
from utils import *
import argparse

# def get_hash(project_path):
#     init_commit = None
#     last_commit = None
#     visited_commit_date = None
#     for commit in Repository(path_to_repo=project_path).traverse_commits():
#         if not visited_commit_date:
#             visited_commit_date = commit.committer_date
#         else:
#             if visited_commit_date > commit.committer_date:
#                 print("reverse!")
#             visited_commit_date = commit.committer_date
#         print(commit.parents)
#         if commit.author_date < conf.dt_start and (not init_commit or commit.author_date > init_commit.author_date):
#             init_commit = commit
#         if commit.author_date < conf.dt_end:
#             last_commit = commit
#         if commit.author_date > conf.dt_end:
#             break
#     print(init_commit.author_date, last_commit.author_date)
#     return init_commit.hash, last_commit.hash

def is_config_file(modified_file, conf):
    path = ""
    if modified_file.new_path:
        path = modified_file.new_path
    elif modified_file.old_path:
        path = modified_file.old_path
    if path == "":
        return False
    if ".git" in path:
        return False
    flag = False
    for suffix in conf.config_file_suffix:
        if path.endswith(suffix):
            flag = True
            break
    return flag


def get_conf_embedding(index, project, content, relpath, namespace, info):
    id = get_hash_sha256(relpath) + "_" + get_hash_sha256(content)
    if os.path.exists(os.path.join(conf.data_path, "db_content", project, info, id + ".json")):
        rec = json.load(open(os.path.join(conf.data_path, "db_content", project, info, id + ".json"), "r"))
        return [{"id": id, "values": rec["embedding"], "metadata": {"path": rec["path"]}}]
    # vectors = index.fetch(ids=[id], namespace=namespace)["vectors"]
    # if len(vectors) != 0:
    #     print("already exist:", id)
    #     return vectors.values
    if info == "test":
        token = get_embedding_tokenizer()
        if len(token.encode(content)) > 8000:
            print("Error: exceed token limit for " + relpath)
            return None
        else:
            embedding = get_embedding(content)['data'][0]['embedding']
            return [{"id": id, "values": embedding, "metadata": {"path": relpath}}]


def get_rel_path(file, project_path):
    return Path(os.path.relpath(file, project_path)).as_posix()


def build_init_conf_db(project, project_path, hash, conf, info):
    if not os.path.exists(os.path.join(conf.data_path, "db_content", project, info)):
        os.makedirs(os.path.join(conf.data_path, "db_content", project, info))
    total_conf_files = 0
    pc = Pinecone(api_key=conf.pinecone_api_key)
    active_indexes = pc.list_indexes()
    index_exist = False
    namespace = hash[:10]
    for index in active_indexes:
        if index["name"] == get_index_name(project, info):
            index_exist = True
            break
    if not index_exist:
        pc.create_index(name=get_index_name(project, info),
                        dimension=1536,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region='us-west-2'))
    index = pc.Index(get_index_name(project, info))
    futures = []
    ids_dict = {}
    if os.path.exists(os.path.join(conf.data_path, "db_content", project, info, "ids.json")):
        ids_dict = json.load(open(os.path.join(conf.data_path, "db_content", project, info, "ids.json"), "r"))
    if namespace in ids_dict.keys():
        print("Skipping building init db for", hash)
        return
    print("Building init db for commit", hash)
    git = Git(project_path)
    files = git.files()
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        for i, file in enumerate(files):
            flag = False
            relpath = get_rel_path(file, project_path)
            for suffix in conf.config_file_suffix:
                if file.endswith(suffix):
                    flag = True
            if flag:
                reader = open(os.path.join(project_path, file), "r", encoding='utf-8')
                content = reader.read()
                total_conf_files += 1
                futures.append(executor.submit(get_conf_embedding, index, project, content, relpath, hash[:10], info))
    ids = []
    print("Number of expected records:", len(futures))
    for future in as_completed(futures):
        res = future.result()
        if res:
            index.upsert(vectors=res, namespace=namespace)
            for rec in res:
                json.dump({"commit_id": hash, "path": rec["metadata"]["path"], "content": content, "embedding": rec["values"]},
                          open(os.path.join(conf.data_path, "db_content", project, info, rec["id"] + ".json"), "w"))
                ids.append(rec["id"])
    # write ids.json
    print("Writing ids.json, do not disturb")
    ids_dict[namespace] = ids
    json.dump(ids_dict, open(os.path.join(conf.data_path, "db_content", project, info, "ids.json"), "w"))


def example(conf):
    prompt = "Who is the winner of 2022 World Cup."
    # # get answer from chatgpt without info
    # response = call_chatgpt_api([prompt], conf.generate_model)
    # print(response["choices"][0]["message"]["content"])
    # init index
    pc = Pinecone(api_key=conf.pinecone_api_key)
    active_indexes = pc.list_indexes()
    index = pc.Index(host='https://test-sreap1y.svc.gcp-starter.pinecone.io')
    # get knowledge
    content = ["Argentina wins the 2022 World Cup.", "Brazil is the most frequent winner of the World Cup."]
    # generate vector and update vector db
    for i, line in enumerate(content):
        data_embedding_res = get_embedding(line)
        upsert_resp = index.upsert(vectors=[("vec_" + str(i), data_embedding_res["data"][0]["embedding"], {"data": line})])
        print(upsert_resp)
    # generate prompt vector
    prompt_embedding = get_embedding(prompt)['data'][0]['embedding']
    # query vector db
    related_vec = index.query(vector=prompt_embedding, top_k=1, include_metadata=True)
    # build prompt with new info
    new_prompt = related_vec["matches"][0]["metadata"]["data"] + " With the information, please answer: "
    new_prompt += prompt
    # get answer from chatgpt
    print(new_prompt)
    response = call_chatgpt_api([new_prompt], conf.generate_model)
    print(response["choices"][0]["message"]["content"])


def sort_parent_commit_by_date(commit_list, project_path, project, info):
    print("Collecting commit list")
    if os.path.exists(os.path.join(conf.data_path, "db_content", project, info, "commit_list_history.json")):
        commit_list_history = json.load(open(os.path.join(conf.data_path, "db_content", project, info, "commit_list_history.json"), "r"))
        if len(commit_list_history["commit_list"]) == len(commit_list):
            return commit_list_history["parent_commit_list"]
    res = {}
    for commit_hash in commit_list:
        for commit in Repository(path_to_repo=project_path, only_commits=[commit_hash]).traverse_commits():
            if len(commit.parents) != 1:
                print("Error: number of parents != 1 for", commit.hash)
            else:
                for parent_commit in Repository(path_to_repo=project_path, only_commits=[commit.parents[0]]).traverse_commits():
                    res[parent_commit.hash] = parent_commit.committer_date
    res = sorted(res.items(), key=lambda x: x[1])
    commit_list_history = {"commit_list": commit_list, "parent_commit_list": [item[0] for item in res]}
    json.dump(commit_list_history, open(os.path.join(conf.data_path, "db_content", project, info, "commit_list_history.json"), "w"))
    return commit_list_history["parent_commit_list"]


def get_last_commit(project_path):
    last_commit = None
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        if not last_commit:
            last_commit = commit
        elif commit.committer_date > last_commit.committer_date:
            last_commit = commit
    return last_commit.hash


def build_commit_conf_db(project, project_path, last_commit, commit_list, conf, info):
    prev_commit = last_commit
    git = Git(project_path)
    ids_dict = json.load(open(os.path.join(conf.data_path, "db_content", project, info, "ids.json"), "r"))
    for j, commit in enumerate(commit_list):
        if commit[:10] in ids_dict.keys():
            print("Skipping collecting vectors for " + commit + " of " + project + " (" + str(j + 1) + "/" + str(len(commit_list)) + ")")
            prev_commit = commit
            continue
        print("Collecting vectors for " + commit + " of " + project + " (" + str(j + 1) + "/" + str(len(commit_list)) + ")")
        pc = Pinecone(api_key=conf.pinecone_api_key)
        index = pc.Index(get_index_name(project, info))
        prev_namespace = prev_commit[:10]
        prev_files = set([id.split("_")[0] for id in ids_dict[prev_namespace]])
        futures = []
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            for i, modified_file in enumerate(git.diff(prev_commit, commit)):
                content = None
                relpath = None
                if not is_config_file(modified_file, conf):
                    continue
                # add file
                if not modified_file.old_path and modified_file.new_path:
                    content = modified_file.source_code
                    relpath = Path(modified_file.new_path).as_posix()
                # remove file
                elif not modified_file.new_path and modified_file.old_path:
                    if get_hash_sha256(Path(modified_file.old_path).as_posix())[:10] not in prev_files:
                        print("Error: not found", modified_file.old_path)
                    else:
                        prev_files.remove(get_hash_sha256(Path(modified_file.old_path).as_posix())[:10])
                # move file or modify file
                elif modified_file.new_path and modified_file.old_path:
                    if get_hash_sha256(Path(modified_file.old_path).as_posix())[:10] not in prev_files:
                        print("Error: not found", modified_file.old_path)
                    else:
                        prev_files.remove(get_hash_sha256(Path(modified_file.old_path).as_posix())[:10])
                    content = modified_file.source_code
                    relpath = Path(modified_file.new_path).as_posix()
                if content:
                    futures.append(executor.submit(get_conf_embedding, index, project, content, relpath, commit[:10], info))
        ids = []
        # upsert updated files to db
        for future in as_completed(futures):
            res = future.result()
            if res:
                index.upsert(vectors=res, namespace=commit[:10])
                for rec in res:
                    json.dump({"commit_id": commit, "path": rec["metadata"]["path"], "content": content, "embedding": rec["values"]},
                              open(os.path.join(conf.data_path, "db_content", project, info, rec["id"] + ".json"), "w"))
                    ids.append(rec["id"])
        # upsert unchanged files to db

        unchanged_ids = []
        for id in ids_dict[prev_namespace]:
            if id.split("_")[0] in prev_files:
                unchanged_ids.append(id)
        for i in range(int(len(unchanged_ids) / 100) + 1):
            idx_start = i * 100
            idx_end = min(i * 100 + 100, len(unchanged_ids))
            if idx_start < idx_end:
                vectors = index.fetch(ids=unchanged_ids[idx_start: idx_end], namespace=prev_namespace)["vectors"]
                if len(vectors.keys()) != len(unchanged_ids[idx_start: idx_end]):
                    print("Error: number of fetched vectors is less than expected: ", len(vectors), len(unchanged_ids[idx_start: idx_end]))
                    print(unchanged_ids[idx_start: idx_end])
                index.upsert(vectors=vectors.values(), namespace=commit[:10])
                ids.extend(vectors.keys())
        # write ids.json
        print("Writing ids.json, do not disturb")
        ids_dict[commit[:10]] = ids
        json.dump(ids_dict, open(os.path.join(conf.data_path, "db_content", project, info, "ids.json"), "w"))
        # iterate prev_commit, sleep to wait for db update
        prev_commit = commit
        time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai_api_key", "-o", help="openai_api_key")
    parser.add_argument("--pinecone_api_key", "-p", help="pinecone_api_key")
    args = parser.parse_args()

    conf = Conf()
    conf.openai_api_key = args.openai_api_key
    conf.pinecone_api_key = args.pinecone_api_key

    if not os.path.exists(conf.data_path):
        os.mkdir(conf.data_path)
    label_path = os.path.join(conf.data_path, "label.csv")
    label_csv = pd.read_csv(label_path)
    # example(conf)
    for project in conf.projects:
        # if project != "dubbo":
        #     continue
        # project_path = os.path.join(conf.repo_path, project)
        # last_commit = get_last_commit(project_path)
        # build_init_conf_db(project, project_path, last_commit, conf, "test")
        # print(len(list(set(label_csv[label_csv["project"] == project]["commit_hash"]))))
        # commit_list = sort_parent_commit_by_date(list(set(label_csv[label_csv["project"] == project]["commit_hash"])), project_path, project, "test")
        # build_commit_conf_db(project, project_path, last_commit, commit_list, conf, "test")
        commit_list = list(set(label_csv[label_csv["project"] == project]["commit_hash"]))
        print(project, len(commit_list))