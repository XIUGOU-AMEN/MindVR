"""检查大模型后端是否真的连通。

页面右上角显示 "LLM 后端 local" 只代表配置值，不代表模型在工作。
本脚本会实际发一次请求，确认连通性与线索抽取效果。

用法：
    python scripts/check_llm.py
    python scripts/check_llm.py --transcript "I am not sad, but I can't sleep at night."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings  # noqa: E402
from backend.llm.base import parse_json_block  # noqa: E402
from backend.llm.factory import build_backend  # noqa: E402
from backend.pipeline.orchestrator import CUE_SYSTEM_PROMPT  # noqa: E402

DEFAULT_TEXT = "I am not sad. But I feel tired and I can't sleep at night."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", default=DEFAULT_TEXT)
    args = parser.parse_args()

    settings = get_settings()
    backend = build_backend()

    print("=" * 62)
    print("大模型后端诊断")
    print("=" * 62)
    print(f"配置值 LLM_BACKEND = {settings.llm_backend}")
    print(f"实际后端 name     = {backend.name}")
    if backend.name == "null":
        print("[fail] 未配置可用后端：LLM_BACKEND 不是 local/maas，或凭据为空")
        raise SystemExit(1)
    if settings.llm_backend == "local":
        print(f"本地地址          = {settings.local_base_url}")
        print(f"本地模型          = {settings.local_model}")
    else:
        print(f"MaaS 地址         = {settings.maas_base_url}")
        print(f"MaaS 模型         = {settings.maas_model}")

    print("-" * 62)
    print("1) 连通性测试 ...")
    try:
        reply = backend.chat("你是一个测试助手。", "请只回复 OK", max_tokens=8)
    except Exception as exc:
        print(f"[fail] 请求失败: {exc.__class__.__name__}: {exc}")
        print("       本地模式：确认 Ollama/vLLM 已启动且地址正确")
        print("       MaaS 模式：确认 endpoint 与 API Key 有效")
        raise SystemExit(1) from exc

    if not reply.strip():
        print("[warn] 服务可连通，但返回为空")
    else:
        print(f"[ok] 返回: {reply.strip()[:60]}")

    print("-" * 62)
    print("2) 线索抽取测试 ...")
    print(f"输入: {args.transcript}")
    try:
        raw = backend.chat(CUE_SYSTEM_PROMPT, args.transcript, max_tokens=512)
        print(f"[debug] 原始返回前 400 字: {raw[:400]!r}")
        data = parse_json_block(raw)
    except Exception as exc:
        print(f"[fail] JSON 抽取失败: {exc}")
        raise SystemExit(1) from exc

    if not data:
        print("[warn] 未解析出 JSON，分析时会回落到规则词典")
    else:
        print(f"[ok] 抽取结果: {data}")
        print("     注意：I am not sad 的『难过』维度应为 0，若为高分说明模型未识别否定")

    print("-" * 62)
    print("诊断完成")


if __name__ == "__main__":
    main()
