"""大模型后端抽象。

比赛演示使用华为云 MaaS，开源复现使用本地 vLLM/Ollama。
两者都提供 OpenAI 兼容接口，因此共享同一实现，只切换 endpoint 与凭据。
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod


class LLMBackend(ABC):
    name: str = "base"

    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        """返回模型原始文本输出。"""

    def chat_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 512,
    ) -> dict:
        """要求模型返回 JSON，解析失败时返回空字典而不是抛错。"""
        text = self.chat(system, user, temperature=0.0, max_tokens=max_tokens)
        return parse_json_block(text)


def parse_json_block(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
