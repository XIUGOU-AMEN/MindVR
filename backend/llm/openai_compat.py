"""OpenAI 兼容后端实现（本地 vLLM/Ollama 与华为云 MaaS 共用）。"""

from __future__ import annotations

import httpx

from backend.llm.base import LLMBackend


class OpenAICompatBackend(LLMBackend):
    def __init__(self, name: str, base_url: str, model: str, api_key: str, timeout: float = 60.0):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "") or ""


class NullBackend(LLMBackend):
    """没有可用模型时占位，保证离线环境整条流水线仍能跑通。"""

    name = "null"

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> str:
        return ""
