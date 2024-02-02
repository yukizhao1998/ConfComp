import argparse

import pandas as pd
from conf import Conf
import os
from tqdm import tqdm
import json
from prompt import *
from chatgpt_api_utils import *
from pinecone import Pinecone, ServerlessSpec
from utils import *
from pydriller import Repository
from pathlib import Path


def eval_file_recall(sub_df, code_change, index, namespace):
    res = []
    query_prompt = query_config_file_prompt(code_change)
    token = get_embedding_tokenizer()
    if len(token.encode(query_prompt)) > 8000:
        print("Error: exceed token limit for " + str(code_change["old_path"]) + " " + str(
            code_change["new_path"]))
        return None
    else:
        embedding = get_embedding(query_prompt)['data'][0]['embedding']
    print(code_change["old_path"], code_change["new_path"])
    for i, row in sub_df.iterrows():
        label = json.loads(row["label"])
        if sum(label.values()) == 0:
            continue
        # do not consider changes that add config files
        if str(row["config_change_old_path"]) == "nan":
            continue
        target = get_hash_sha256(Path(row["config_change_old_path"]).as_posix())[:10]
        resp = index.query(vector=embedding, namespace=namespace, top_k=1000, include_values=False)
        rank = -1
        if len(resp["matches"]) == 0:
            print("Error: no response matches return")
        for i, item in enumerate(resp["matches"]):
            if item["id"].startswith(target):
                rank = i
        print(row["config_change_old_path"], target, rank)
        res.append(rank)


def evaluate(project, project_path, label_csv, conf, mode):
    commit_list = list(set(label_csv[label_csv["project"] == project]["commit_hash"]))
    print("Begin testing " + str(len(commit_list)) + " cases under " + mode + " for " + project)
    pc = Pinecone(api_key=conf.pinecone_api_key)
    for commit in tqdm(commit_list):
        # if commit != "970964a01259e589e22ac96d324658232c205081":
        #     continue
        parent_commit = None
        for c in Repository(path_to_repo=project_path, only_commits=[commit]).traverse_commits():
            if len(c.parents) != 1:
                print("Error: number of parents != 1 for", c.hash)
                continue
            else:
                parent_commit = c.parents[0]
        df = label_csv[label_csv["commit_hash"] == commit]
        code_changes = json.load(open(os.path.join(conf.data_path, "commit_config_related_raw", project, commit + ".json"), "r"))["code_change_chunks"]
        print(commit, parent_commit)
        for code_change in code_changes:
            if code_change["old_path"]:
                sub_df = df[df["code_change_old_path"] == code_change["old_path"]]
            else:
                sub_df = df[df["code_change_new_path"] == code_change["new_path"]]
            eval_file_recall(sub_df, code_change, pc.Index(get_index_name(project, mode)), parent_commit[:10])




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai_api_key", "-o", help="openai_api_key")
    parser.add_argument("--pinecone_api_key", "-p", help="pinecone_api_key")
    args = parser.parse_args()

    conf = Conf()
    conf.openai_api_key = args.openai_api_key
    conf.pinecone_api_key = args.pinecone_api_key

    label_path = os.path.join(conf.data_path, "label.csv")
    label_csv = pd.read_csv(label_path)
    for project in conf.projects:
        if project != "dubbo":
            continue
        project_path = os.path.join(conf.repo_path, project)
        evaluate(project, project_path, label_csv, conf, "test")
