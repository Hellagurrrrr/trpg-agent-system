import os
import json
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

API_KEY = os.getenv("ZAI_API_KEY")
if not API_KEY:
    raise ValueError("未找到 ZAI_API_KEY，请检查 .env 文件。")


client = OpenAI(
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)


def chat_once(user_message: str, system_message: str = "你是一个有帮助的助手。") -> str:
    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def chat_json(system_message: str, user_message: str) -> dict:
    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    return json.loads(content)