from conf import Conf
import openai
import requests
import tiktoken


def call_chatgpt_api(messages):
    conf = Conf()
    messages = list(map(lambda chunk: {
        "role": "user",
        "content": chunk
    }, messages))
    openai.api_key = conf.openai_api_key
    response = openai.ChatCompletion.create(
        model=conf.label_model,
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



def get_label_tokenizer():
    conf = Conf()
    return tiktoken.encoding_for_model(conf.label_model)


if __name__ == "__main__":
    messages, response = call_chatgpt_api_multi([], ["I want to go to Florence this summer.", "Where should I visit?"])
    ans = response["choices"][0]["message"]["content"]
    session_id = response["id"]

    print(ans)
    messages.append({"role": "assistant", "content": ans})
    messages, response = call_chatgpt_api_multi(messages, "Repeat what you said just now.")
    ans = response["choices"][0]["message"]["content"]
    print(ans)

