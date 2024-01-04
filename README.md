# Introduction

This is a project for predicting code-change-induced configuration changes.

# Prepare Data

## Download repositories

We use the most popular Apache Java repositories (up to Dec 2023) in our projects. 

Go under `/repos`, and run `sh download_repos.sh` to download repositories.

## Install dependencies

Go under the project root directory and run `pip install requirements.txt` to install necessary dependencies.

## Modify configurations

Before starting to label the data, modify configurations in `conf.py` to fit in your settings, e.g. OpenAI accounts. Here are the import configurations you should modify before moving on:

1. `self.openai_api_key`: fill in your openai api key.
2. `self.label_model`: fill in the expected model for labeling the data, e.g. gpt-4 or gpt-4-turbo.

## Labeling configuration change chunks using ChatGPT

Go under the project root directory and run `py prepare_data.py` to extract history commits and label code-change-induced configuration changes.

### Extract history commits

This step extract history commits of the projects that contain both the code and configuration file changes. We identify the code files with suffix `.java`, and the configuration files with suffixes `.xml/.properties/.json/.yaml/.yml`.

Data of the commits is saved in `./data/commit_config_related_raw/*project_name*/*commit_id*.json`. In the json file, we save the new path, old path, and diff chunks of each code changes and configuration changes.

### Label code-change-induced configuration changes

This step label whether each configuration change chunk is related to the code changes using ChatGPT. We first build prompts to ask ChatGPT whether each chunks of a configuration change is related to the changes to a code file. Following CoT techniques, we lead ChatGPT to think step by step. Here is an example the prompt format.

> Here is the diff of a code change. The path of the changed file is ***. There are 2 diff chunk(s) in total.
>
> chunk 1:
>
> ...
>
> chunk 2:
>
> ...
>
> Here is the diff of a configuration change. The path of the changed file is ***. There are 1 diff chunk(s) in total.
>
> chunk1:
>
> ...
>
> Given the code change and configuration change, which diff chunks of the configuration change are induced by the code change? Let's think step by step.

After ChatGPT returns a response, we further attach the response to a  prompt which instruct ChatGPT to format the response. Here is an example the prompt format.

>Respond in a json format with the chunk as the key and whether the 1 diff chunk(s) is/are induced by the code change as value (0: False, 1: True), similar as the following: {"chunk 1": 0}

We collect the responses which are in the json format, and build the labeling dataset saved in `./data/label.csv`. Here is the columns of the file:

> project,commit_hash,code_change_old_path,code_change_new_path,config_change_old_path,config_change_new_path,label

There is an example in `exapmle/label.csv`.