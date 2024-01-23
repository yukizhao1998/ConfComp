import os
import openai
import pinecone
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from pydriller import Git, Repository
from conf import Conf
import pandas as pd


def get_hash(project_path):
    init_commit = None
    last_commit = None
    visited_commit_date = None
    for commit in Repository(path_to_repo=project_path).traverse_commits():
        if not visited_commit_date:
            visited_commit_date = commit.committer_date
        else:
            if visited_commit_date > commit.committer_date:
                print("reverse!")
            visited_commit_date = commit.committer_date
        print(commit.parents)
        if commit.author_date < conf.dt_start and (not init_commit or commit.author_date > init_commit.author_date):
            init_commit = commit
        if commit.author_date < conf.dt_end:
            last_commit = commit
        if commit.author_date > conf.dt_end:
            break
    print(init_commit.author_date, last_commit.author_date)
    return init_commit.hash, last_commit.hash


def update_db(project_path, commit_list):
    last_commit = None
    for commit in Repository(path_to_repo=project_path, only_commits=commit_list).traverse_commits():
        parents = commit.parents
        if len(parents) != 1:
            print("Error: parents length > 1 for " + commit.hash)
            continue
        if not last_commit:
            last_commit = commit.hash


if __name__ == "__main__":
    conf = Conf()
    if not os.path.exists(conf.data_path):
        os.mkdir(conf.data_path)
    label_path = os.path.join(conf.data_path, "label.csv")
    label_csv = pd.read_csv(label_path)
    for project in conf.projects:
        if project != "dubbo":
            continue
        project_path = os.path.join(conf.repo_path, project)
        commit_list = list(set(label_csv[label_csv["project"] == project]["commit_hash"]))
        print(commit_list)
        update_db(project_path, commit_list)
        # project_path = os.path.join(conf.repo_path, project)
        # init_hash, last_hash = get_hash(project_path)
        # print(project, init_hash, last_hash)
        # git = Git(project_path)
        # git.checkout(init_hash)
        # # print(git.files())
        # git.checkout(last_hash)
        # git.diff()