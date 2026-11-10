"""特征抽取。

文本语义特征由规则词典 + 可选大模型补强得到；
声学与视觉特征在演示模式下使用预提取文件或群体中位数填充。
生产环境接入 openSMILE / OpenFace 的方式见 docs/ARCHITECTURE.md。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

FEATURE_NAMES: list[str] = [
    "neg_sentiment_ratio",
    "first_person_ratio",
    "self_negation_ratio",
    "sleep_mention",
    "anhedonia_mention",
    "fatigue_mention",
    "worthlessness_mention",
    "concentration_mention",
    "appetite_mention",
    "psychomotor_mention",
    "word_count",
    "avg_sentence_len",
    "f0_mean",
    "f0_std",
    "energy_mean",
    "speech_rate",
    "pause_ratio",
    "jitter",
    "shimmer",
    "au_intensity_mean",
    "au_intensity_std",
    "gaze_away_ratio",
    "smile_freq",
    "head_motion",
]

FEATURE_LABELS: dict[str, str] = {
    "neg_sentiment_ratio": "负面情绪表达比例",
    "first_person_ratio": "第一人称自我提及",
    "self_negation_ratio": "自我否定表述",
    "sleep_mention": "睡眠问题提及",
    "anhedonia_mention": "兴趣丧失提及",
    "fatigue_mention": "精力不足提及",
    "worthlessness_mention": "自我价值感低提及",
    "concentration_mention": "注意力困难提及",
    "appetite_mention": "食欲变化提及",
    "psychomotor_mention": "动作迟缓或烦躁提及",
    "word_count": "发言词数",
    "avg_sentence_len": "平均句长",
    "f0_mean": "基频均值",
    "f0_std": "基频波动",
    "energy_mean": "语音能量",
    "speech_rate": "语速",
    "pause_ratio": "停顿比例",
    "jitter": "频率微扰",
    "shimmer": "振幅微扰",
    "au_intensity_mean": "面部动作单元强度",
    "au_intensity_std": "面部表情变化幅度",
    "gaze_away_ratio": "视线回避比例",
    "smile_freq": "微笑频率",
    "head_motion": "头部运动量",
}

DEFAULT_VALUES: dict[str, float] = {
    "neg_sentiment_ratio": 0.25,
    "first_person_ratio": 0.35,
    "self_negation_ratio": 0.10,
    "sleep_mention": 0.15,
    "anhedonia_mention": 0.12,
    "fatigue_mention": 0.14,
    "worthlessness_mention": 0.10,
    "concentration_mention": 0.10,
    "appetite_mention": 0.08,
    "psychomotor_mention": 0.08,
    "word_count": 180.0,
    "avg_sentence_len": 12.0,
    "f0_mean": 145.0,
    "f0_std": 28.0,
    "energy_mean": 0.55,
    "speech_rate": 3.4,
    "pause_ratio": 0.28,
    "jitter": 0.012,
    "shimmer": 0.055,
    "au_intensity_mean": 0.42,
    "au_intensity_std": 0.18,
    "gaze_away_ratio": 0.32,
    "smile_freq": 0.20,
    "head_motion": 0.30,
}

NEGATIVE_WORDS = [
    "难过", "痛苦", "焦虑", "害怕", "绝望", "孤独", "没意思", "烦", "累", "压力",
    "不开心", "失眠", "想哭", "无望", "空", "麻木", "崩溃",
    "sad", "depressed", "anxious", "hopeless", "lonely", "miserable", "empty",
    "numb", "upset", "stressed", "angry", "afraid", "cry", "tired",
]

FIRST_PERSON_WORDS = ["我", "自己", "我的", "本人"]
FIRST_PERSON_PATTERN = re.compile(r"\b(i|me|my|myself|mine)\b", re.IGNORECASE)

SELF_NEGATION_PATTERNS = [
    r"我不行", r"我没用", r"我做不好", r"我很失败", r"我不够好",
    r"都是我的错", r"我拖累", r"我一无是处",
    r"\bi'?m (useless|worthless|a failure|not good enough|nothing)\b",
    r"\bi hate myself\b",
    r"\bit'?s my fault\b",
    r"\bi'?m a burden\b",
    r"\bi can'?t do anything\b",
]

CUE_DICTIONARY: dict[str, list[str]] = {
    "sleep_mention": [
        "失眠", "睡不着", "睡不好", "早醒", "睡眠", "多梦", "嗜睡",
        "insomnia", "can't sleep", "cant sleep", "sleep badly", "wake up early", "nightmare",
    ],
    "anhedonia_mention": [
        "没兴趣", "不想做", "没意思", "提不起", "失去兴趣", "不想见人",
        "no interest", "lost interest", "don't enjoy", "dont enjoy", "not fun", "nothing fun",
        "don't want to do", "dont want to do",
    ],
    "fatigue_mention": [
        "很累", "没力气", "疲惫", "乏力", "精力不足", "不想动",
        "tired", "exhausted", "no energy", "fatigue", "drained", "worn out",
    ],
    "worthlessness_mention": [
        "没用", "失败", "自责", "没价值", "对不起", "拖累",
        "worthless", "useless", "a failure", "blame myself", "my fault", "burden",
    ],
    "concentration_mention": [
        "注意力", "集中不了", "记不住", "走神", "脑子慢",
        "can't focus", "cant focus", "can't concentrate", "cant concentrate",
        "distracted", "forgetful", "mind goes blank",
    ],
    "appetite_mention": [
        "吃不下", "没胃口", "暴食", "食欲", "体重下降", "不想吃",
        "no appetite", "can't eat", "cant eat", "overeating", "lost weight", "not hungry",
    ],
    "psychomotor_mention": [
        "坐立不安", "动不了", "很慢", "烦躁", "静不下来",
        "restless", "can't sit still", "cant sit still", "slowed down", "agitated",
    ],
}

SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]+")
HANZI = re.compile(r"[\u4e00-\u9fff]")
WORD_TOKEN = re.compile(r"[a-z']+")
CLAUSE_SEPARATORS = (".", "!", "?", "。", "！", "？", ";", "；", ",", "，")

NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "none",
    "nobody",
    "nothing",
    "neither",
    "nor",
    "hardly",
    "barely",
    "without",
    "cannot",
    "cant",
    "can't",
    "dont",
    "don't",
    "doesnt",
    "doesn't",
    "didnt",
    "didn't",
    "isnt",
    "isn't",
    "arent",
    "aren't",
    "wasnt",
    "wasn't",
    "werent",
    "weren't",
    "wont",
    "won't",
    "wouldnt",
    "wouldn't",
    "couldnt",
    "couldn't",
    "shouldnt",
    "shouldn't",
}

CHINESE_NEGATION = ("不", "没", "无", "非", "别", "未", "莫")


def _is_negated(lowered_text: str, cue_start: int) -> bool:
    """判断某个线索词是否处于否定语境，避免把 “not sad” 算成负面。"""
    prefix = lowered_text[max(0, cue_start - 28) : cue_start]
    cut = max((prefix.rfind(sep) for sep in CLAUSE_SEPARATORS), default=-1)
    if cut != -1:
        prefix = prefix[cut + 1 :]

    tokens = WORD_TOKEN.findall(prefix)
    if tokens and any(token in NEGATION_TOKENS for token in tokens[-2:]):
        return True
    return any(char in CHINESE_NEGATION for char in prefix[-3:])


def _count_cues(text: str, cues: list[str]) -> int:
    lowered = text.lower()
    total = 0
    for cue in cues:
        needle = cue.lower()
        start = 0
        while True:
            index = lowered.find(needle, start)
            if index == -1:
                break
            if not _is_negated(lowered, index):
                total += 1
            start = index + len(needle)
    return total


def _normalize_count(count: int, cap: int = 3) -> float:
    return min(count, cap) / cap


def extract_text_features(transcript: str) -> dict[str, float]:
    text = (transcript or "").strip()
    if not text:
        return {}

    sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()]
    n_sentences = max(len(sentences), 1)
    hanzi_count = len(HANZI.findall(text))
    latin_words = len(re.findall(r"[A-Za-z']+", text))
    word_count = float(hanzi_count + latin_words)

    neg_count = _count_cues(text, NEGATIVE_WORDS)
    first_person_count = sum(text.count(word) for word in FIRST_PERSON_WORDS)
    first_person_count += len(FIRST_PERSON_PATTERN.findall(text))
    self_neg_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in SELF_NEGATION_PATTERNS)

    features: dict[str, float] = {
        "neg_sentiment_ratio": min(neg_count / n_sentences, 1.0),
        "first_person_ratio": min(first_person_count / n_sentences, 1.0),
        "self_negation_ratio": min(self_neg_count / n_sentences, 1.0),
        "word_count": word_count,
        "avg_sentence_len": word_count / n_sentences,
    }

    for feature, cues in CUE_DICTIONARY.items():
        features[feature] = _normalize_count(_count_cues(text, cues))

    return features


def load_precomputed(path: str | Path | None) -> dict[str, float]:
    """读取 openSMILE/OpenFace 预提取的特征文件（JSON）。"""
    if not path:
        return {}
    file = Path(path)
    if not file.exists():
        return {}
    with file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {k: float(v) for k, v in data.items() if k in FEATURE_NAMES}


def merge_features(
    text_features: dict[str, float],
    acoustic: dict[str, float] | None = None,
    visual: dict[str, float] | None = None,
) -> dict[str, float]:
    merged: dict[str, float] = dict(DEFAULT_VALUES)
    merged.update(text_features)
    merged.update(acoustic or {})
    merged.update(visual or {})
    return merged


def to_vector(features: dict[str, float]) -> np.ndarray:
    return np.array(
        [float(features.get(name, DEFAULT_VALUES[name])) for name in FEATURE_NAMES],
        dtype=np.float64,
    ).reshape(1, -1)


def vector_to_features(vector: np.ndarray) -> dict[str, float]:
    flat = np.asarray(vector).reshape(-1)
    return {name: float(flat[i]) for i, name in enumerate(FEATURE_NAMES)}
