from conf import Conf
import openai
import requests


def call_chatgpt_api(messages):
    conf = Conf()
    messages = list(map(lambda chunk: {
        "role": "user",
        "content": chunk
    }, messages))
    openai.api_key = conf.openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=1024,
        temperature=0.5
    )
    return response