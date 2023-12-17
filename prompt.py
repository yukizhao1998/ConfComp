def line_prompt(lines):
    if len(lines) == 1:
        return " [line " + str(lines[0][0]) + "]"
    else:
        return " [line " + str(lines[0][0]) + "-" + str(lines[-1][0]) + "]"


def chunk_prompt(diff_chunk):
    if len(diff_chunk) == 0:
        return ""
    prompt = ""
    cnt = 1
    prompt += "There are " + str(len(diff_chunk)) + " diff chunk(s) in total.\n"
    for chunk in diff_chunk:
        prompt += "chunk " + str(cnt) + ":\n"
        if len(chunk["deleted"]) > 0:
            prompt += "deleted line(s)" + line_prompt(chunk["deleted"]) + ":\n"
            for line in chunk["deleted"]:
                prompt += line[1] + "\n"
        if len(chunk["added"]) > 0:
            prompt += "added line(s)" + line_prompt(chunk["added"]) + ":\n"
            for line in chunk["added"]:
                prompt += line[1] + "\n"
        cnt += 1
    return prompt


def path_prompt(change):
    prompt = ""
    if not change["old_path"]:
        prompt += "The change creates a new file, whose path is " + change["new_path"] + ". "
    elif not change["new_path"]:
        prompt += "The change deletes a new file, whose path is " + change["new_path"] + ". "
    elif change["old_path"] == change["new_path"]:
        prompt += "The path of the changed file is " + change["new_path"] + ". "
    elif change["old_path"] != change["new_path"]:
        prompt += "The change moves the file whose path is " + change["old_path"] + \
                                " to a new path at " + change["new_path"] + ". "
    return prompt


def label_question_prompt():
    prompt = ""
    # prompt += "Given the code change and configuration change, which diff chunks of the configuration change " + \
    #           "are induced by the code change? How confident are you? Confidence score: 0 (not confident), " + \
    #           "1 (confident), 2 (very confident). "
    # prompt += "Respond in a json format with the chunk as the key and the confidence as the value, " + \
    #           "similar as the following: \n"
    # prompt += "{\"chunk 1\": 0, \"chunk 3\": 2}\n"
    prompt += "Given the code change and configuration change, which diff chunks of the configuration change " + \
              "are induced by the code change? "
    prompt += "Respond in a json format with the chunk as the key and whether the diff chunk is induced by the code " + \
              "change as value (0: False, 1: True), similar as the following: \n"
    prompt += "{\"chunk 1\": 0, \"chunk 2\": 0}\n"
    return prompt


def label_query_prompt(code_change, config_change):
    prompt = []
    code_change_prompt = ""
    code_change_prompt += "Here is the diff of a code change. "
    code_change_prompt += path_prompt(code_change)
    code_change_prompt += chunk_prompt(code_change["chunks"])
    prompt.append(code_change_prompt)
    config_change_prompt = ""
    config_change_prompt += "Here is the diff of a configuration change. "
    config_change_prompt += path_prompt(config_change)
    config_change_prompt += chunk_prompt(config_change["chunks"])
    prompt.append(config_change_prompt)
    prompt.append(label_question_prompt())
    return prompt

