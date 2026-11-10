"""生成完全合成的演示数据。

用途：
1. 让仓库在没有任何真实数据的情况下也能端到端跑通；
2. 为单元测试提供稳定输入。

注意：所有 participant_id 均为 demo_xxxx，数据由随机过程生成，
与任何真实受试者无关，不含任何 DAIC-WOZ 内容，可安全开源。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.features import FEATURE_NAMES  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
N_SAMPLES = 240
SEED = 20260101

TEMPLATES = {
    "low": [
        "最近状态还不错，睡得挺好，白天也有精神。周末会和朋友出去走走，工作也顺利。",
        "我最近挺好的，吃饭睡觉都正常，偶尔有点压力但能调整过来。",
        "没有什么特别的困扰，生活比较规律，和家人相处也愉快。",
    ],
    "mid": [
        "有时候会睡不好，早上起来还是觉得累。工作忙的时候有点烦，但还能坚持。",
        "最近偶尔提不起劲，不太想出门，不过休息一下会好一点。",
        "压力有点大，注意力不太集中，吃饭也没什么胃口。",
    ],
    "high": [
        "这段时间一直失眠，晚上两三点就醒了，白天完全没力气。以前喜欢的事情现在一点兴趣都没有。",
        "我觉得自己很没用，总是拖累家里人，什么都做不好，也不知道该怎么办。",
        "脑子转不动，注意力集中不了，不想吃东西，也不想见人，觉得活着没什么意思。",
    ],
}


def _clip01(value: np.ndarray) -> np.ndarray:
    return np.clip(value, 0.0, 1.0)


def build_frame(rng: np.random.Generator, n: int) -> pd.DataFrame:
    latent = rng.normal(0.0, 1.0, n)
    score = np.clip(np.round(9.0 + 5.2 * latent + rng.normal(0, 1.1, n)), 0, 24).astype(int)

    data: dict[str, np.ndarray] = {}
    data["neg_sentiment_ratio"] = _clip01(0.22 + 0.16 * latent + rng.normal(0, 0.05, n))
    data["first_person_ratio"] = _clip01(0.32 + 0.10 * latent + rng.normal(0, 0.05, n))
    data["self_negation_ratio"] = _clip01(0.08 + 0.12 * latent + rng.normal(0, 0.04, n))
    data["sleep_mention"] = _clip01(0.15 + 0.22 * latent + rng.normal(0, 0.06, n))
    data["anhedonia_mention"] = _clip01(0.12 + 0.24 * latent + rng.normal(0, 0.06, n))
    data["fatigue_mention"] = _clip01(0.14 + 0.23 * latent + rng.normal(0, 0.06, n))
    data["worthlessness_mention"] = _clip01(0.08 + 0.20 * latent + rng.normal(0, 0.05, n))
    data["concentration_mention"] = _clip01(0.10 + 0.20 * latent + rng.normal(0, 0.05, n))
    data["appetite_mention"] = _clip01(0.08 + 0.18 * latent + rng.normal(0, 0.05, n))
    data["psychomotor_mention"] = _clip01(0.07 + 0.17 * latent + rng.normal(0, 0.05, n))
    data["word_count"] = np.clip(190 - 35 * latent + rng.normal(0, 25, n), 40, 520)
    data["avg_sentence_len"] = np.clip(12.5 - 1.6 * latent + rng.normal(0, 1.2, n), 5, 25)
    data["f0_mean"] = 146 - 9 * latent + rng.normal(0, 6, n)
    data["f0_std"] = np.clip(29 + 4 * latent + rng.normal(0, 3, n), 8, 60)
    data["energy_mean"] = _clip01(0.56 - 0.09 * latent + rng.normal(0, 0.05, n))
    data["speech_rate"] = np.clip(3.5 - 0.35 * latent + rng.normal(0, 0.25, n), 1.5, 6.0)
    data["pause_ratio"] = _clip01(0.27 + 0.09 * latent + rng.normal(0, 0.04, n))
    data["jitter"] = np.clip(0.011 + 0.004 * latent + rng.normal(0, 0.0015, n), 0.002, 0.05)
    data["shimmer"] = np.clip(0.052 + 0.012 * latent + rng.normal(0, 0.005, n), 0.01, 0.2)
    data["au_intensity_mean"] = _clip01(0.44 - 0.07 * latent + rng.normal(0, 0.05, n))
    data["au_intensity_std"] = _clip01(0.19 + 0.05 * latent + rng.normal(0, 0.04, n))
    data["gaze_away_ratio"] = _clip01(0.30 + 0.12 * latent + rng.normal(0, 0.05, n))
    data["smile_freq"] = _clip01(0.24 - 0.10 * latent + rng.normal(0, 0.05, n))
    data["head_motion"] = _clip01(0.30 + 0.08 * latent + rng.normal(0, 0.05, n))

    frame = pd.DataFrame({name: data[name] for name in FEATURE_NAMES})
    frame.insert(0, "phq8_binary", (score >= 10).astype(int))
    frame.insert(0, "phq8_score", score)
    frame.insert(0, "participant_id", [f"demo_{i:04d}" for i in range(n)])
    return frame


def build_transcripts(rng: np.random.Generator, frame: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in frame.iterrows():
        score = int(row["phq8_score"])
        bucket = "low" if score < 5 else ("mid" if score < 10 else "high")
        options = TEMPLATES[bucket]
        rows.append(
            {
                "participant_id": row["participant_id"],
                "phq8_score": score,
                "transcript": options[int(rng.integers(0, len(options)))],
            }
        )
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    frame = build_frame(rng, N_SAMPLES)
    frame.to_csv(OUTPUT_DIR / "features_demo.csv", index=False)

    transcripts = build_transcripts(rng, frame)
    with (OUTPUT_DIR / "transcripts_demo.jsonl").open("w", encoding="utf-8") as handle:
        for item in transcripts:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"已生成 {len(frame)} 条合成样本 -> {OUTPUT_DIR}")
    print(f"抑郁比例: {frame['phq8_binary'].mean():.1%}")


if __name__ == "__main__":
    main()
