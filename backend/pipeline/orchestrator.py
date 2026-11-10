"""分析编排：文本线索 -> 特征融合 -> 模型推理 -> 结构化结果。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from backend.config import get_settings
from backend.llm.base import LLMBackend
from backend.llm.factory import build_backend
from backend.pipeline.features import (
    CUE_DICTIONARY,
    extract_text_features,
    load_precomputed,
    merge_features,
)
from backend.pipeline.regress import DepressionModel

CUE_SYSTEM_PROMPT = (
    "你是心理健康访谈的文本标注助手。请只依据给定文本判断症状提及强度，不做诊断、不编造。"
    "输出严格 JSON，键为睡眠、兴趣、精力、自我价值、注意力、食欲、动作迟缓七个维度。"
    "值为 0 到 3 的整数：0 表示未提及或明确否认（如 I am not sad、我没有失眠），"
    "1 表示轻微或笼统提及，2 表示明确描述，3 表示持续且严重的困扰。"
    "必须区分『提及』与『否认』，被否定的症状一律计 0。"
)

CUE_KEYS = {
    "sleep_mention": "睡眠",
    "anhedonia_mention": "兴趣",
    "fatigue_mention": "精力",
    "worthlessness_mention": "自我价值",
    "concentration_mention": "注意力",
    "appetite_mention": "食欲",
    "psychomotor_mention": "动作迟缓",
}

_model_cache: DepressionModel | None = None


def get_model() -> DepressionModel | None:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    path: Path = get_settings().model_file
    if not path.exists():
        return None
    _model_cache = DepressionModel.load(path)
    return _model_cache


def reset_model_cache() -> None:
    global _model_cache
    _model_cache = None


def llm_cue_features(transcript: str, backend: LLMBackend) -> dict[str, float]:
    """用大模型补强规则词典，失败时静默回落到纯规则结果。"""
    if not transcript.strip() or backend.name == "null":
        return {}
    user_prompt = f"访谈文本：\n{transcript[:4000]}"
    try:
        data = backend.chat_json(CUE_SYSTEM_PROMPT, user_prompt, max_tokens=512)
    except Exception:
        return {}

    features: dict[str, float] = {}
    for feature, label in CUE_KEYS.items():
        raw = data.get(label, data.get(feature))
        if isinstance(raw, (int, float)):
            features[feature] = float(min(max(raw, 0), 3)) / 3.0
    return features


def analyze_features(
    participant_id: str,
    transcript: str,
    extra_features: dict[str, float] | None = None,
    acoustic_path: str | None = None,
    visual_path: str | None = None,
    use_llm: bool = True,
) -> dict:
    started = time.perf_counter()
    model = get_model()
    if model is None:
        raise RuntimeError("模型文件不存在，请先运行 python scripts/train.py")

    text_features = extract_text_features(transcript)
    if use_llm:
        backend = build_backend()
        text_features.update(llm_cue_features(transcript, backend))
    else:
        backend = build_backend()

    merged = merge_features(
        text_features,
        acoustic=load_precomputed(acoustic_path),
        visual=load_precomputed(visual_path),
    )
    if extra_features:
        merged.update(extra_features)

    prediction = model.predict(merged)
    latency_ms = int((time.perf_counter() - started) * 1000)

    return {
        "participant_id": participant_id,
        **prediction,
        "transcript_excerpt": transcript[:160],
        "model_version": model.version,
        "llm_backend": backend.name,
        "latency_ms": latency_ms,
    }


def cue_dictionary_json() -> str:
    return json.dumps(CUE_DICTIONARY, ensure_ascii=False, indent=2)
