"""根据配置构建大模型后端。"""

from __future__ import annotations

from backend.config import Settings, get_settings
from backend.llm.base import LLMBackend
from backend.llm.openai_compat import NullBackend, OpenAICompatBackend


def build_backend(settings: Settings | None = None) -> LLMBackend:
    settings = settings or get_settings()

    if settings.llm_backend == "maas":
        if not settings.maas_base_url or not settings.maas_api_key:
            return NullBackend()
        return OpenAICompatBackend(
            name="maas",
            base_url=settings.maas_base_url,
            model=settings.maas_model,
            api_key=settings.maas_api_key,
            timeout=30.0,
        )

    if settings.llm_backend == "local":
        return OpenAICompatBackend(
            name="local",
            base_url=settings.local_base_url,
            model=settings.local_model,
            api_key=settings.local_api_key,
            timeout=8.0,
        )

    return NullBackend()
