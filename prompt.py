def line_prompt(lines):
    if len(lines) == 1:
        return " [line " + str(lines[0][0]) + "]"
    else:
        return " [line " + str(lines[0][0]) + "-" + str(lines[-1][0]) + "]"


def chunk_prompt(diff_chunk):
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