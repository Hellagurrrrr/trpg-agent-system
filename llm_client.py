"""
与智谱 OpenAI 兼容接口的轻量封装；PM/DM 的 JSON 模式走 chat_json_stream（流式）或 chat_json（整包）。
密钥来自环境变量，避免把 API Key 写进仓库。
"""
from __future__ import annotations

import json
import os
from typing import Callable, Optional

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

API_KEY = os.getenv("ZAI_API_KEY")
if not API_KEY:
    raise ValueError("未找到 ZAI_API_KEY，请检查 .env 文件。")

# base_url 指向智谱兼容端点；model 名称需与控制台可用模型一致
client = OpenAI(
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

DEFAULT_MODEL = "glm-4.7"


def chat_once(user_message: str, system_message: str = "你是一个有帮助的助手。") -> str:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def chat_once_stream(
    user_message: str,
    system_message: str = "你是一个有帮助的助手。",
    *,
    on_chunk: Optional[Callable[[str], None]] = None,
    temperature: float = 0.3,
) -> str:
    """非 JSON 的流式补全；on_chunk 收到每个文本增量（不传则仅聚合全文）。"""
    stream = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        stream=True,
    )
    parts: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            parts.append(delta)
            if on_chunk:
                on_chunk(delta)
    return "".join(parts)


def chat_json(system_message: str, user_message: str) -> dict:
    """非流式 JSON；兼容旧调用或流式不可用时回退。"""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("模型返回空内容")
    return json.loads(content)


def chat_json_stream(
    system_message: str,
    user_message: str,
    *,
    temperature: float = 0,
    stream_label: str = "",
    on_chunk: Optional[Callable[[str], None]] = None,
    echo: bool = True,
) -> dict:
    """
    流式请求 JSON Object：逐块收取，整段拼齐后 json.loads。
    - stream_label：非空时先打印一行标题。
    - on_chunk：自定义每块处理；若为空且 echo=True，则默认 print(块, end='', flush=True)。
    """
    try:
        stream = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            stream=True,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        # 少数兼容实现不支持「流式 + json_object」组合，回退为整包请求
        print(f"[llm] 流式 JSON 不可用（{exc}），已回退为非流式。")
        return chat_json(system_message, user_message)

    parts: list[str] = []
    header_printed = False

    def _emit(text: str) -> None:
        if on_chunk:
            on_chunk(text)
        elif echo:
            print(text, end="", flush=True)

    try:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if not delta:
                continue
            if stream_label and not header_printed:
                print(f"\n── {stream_label} · 流式输出 ──", flush=True)
                header_printed = True
            parts.append(delta)
            _emit(delta)
    except Exception as exc:
        print(f"\n[llm] 流式读取中断（{exc}），已回退为非流式。")
        return chat_json(system_message, user_message)

    if echo and on_chunk is None and parts:
        print(flush=True)

    raw = "".join(parts)
    if not raw.strip():
        raise ValueError("流式响应为空")
    return json.loads(raw)
