from conf import Conf
import openai
import requests
import tiktoken
import time


def call_chatgpt_api(messages, model=Conf().label_model):
    conf = Conf()
    messages = list(map(lambda chunk: {
        "role": "user",
        "content": chunk
    }, messages))
    openai.api_key = conf.openai_api_key
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        max_tokens=4000,
        temperature=0.5
    )
    return response


def call_chatgpt_api_multi(history, message_text):
    conf = Conf()
    for text in message_text:
        history.append({"role": "user", "content": text})
    messages = history
    openai.api_key = conf.openai_api_key
    response = openai.ChatCompletion.create(
        model=conf.label_model,
        messages=messages,
        temperature=0.5
    )
    return messages, response


def get_embedding(content):
    while True:
        try:
            conf = Conf()
            openai.api_key = conf.openai_api_key
            response = openai.Embedding.create(
            model=conf.openai_embedding_model,
            input=content
            )
            return response
        except Exception as e:
            print("Retry...")
            time.sleep(10)


def get_label_tokenizer():
    conf = Conf()
    return tiktoken.encoding_for_model(conf.label_model)


def get_embedding_tokenizer():
    conf = Conf()
    return tiktoken.encoding_for_model(conf.openai_embedding_model)


if __name__ == "__main__":
    messages, response = call_chatgpt_api_multi([], ["I want to go to Florence this summer.", "Where should I visit?"])
    ans = response["choices"][0]["message"]["content"]
    session_id = response["id"]

    print(ans)
    messages.append({"role": "assistant", "content": ans})
    messages, response = call_chatgpt_api_multi(messages, "Repeat what you said just now.")
    ans = response["choices"][0]["message"]["content"]
    print(ans)

