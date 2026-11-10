"""批量构建真实 DAIC-WOZ 特征表（优先使用官方特征 CSV）。

数据来源优先级：
1. features/*_OpenSMILE2.3.0_egemaps.csv  → 声学 7 维
2. features/*_OpenFace2.1.0_Pose_gaze_AUs.csv → 视觉 5 维
3. 缺少官方特征时，回退到本地 numpy 声学提取

文本 12 维来自 *_Transcript.csv 的规则抽取。
最终与 full_split.csv 的 PHQ_Score / PHQ_Binary 对齐。

用法：
    python scripts/build_real_dataset.py --limit 10
    python scripts/build_real_dataset.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.features import FEATURE_NAMES, extract_text_features, merge_features  # noqa: E402
from backend.pipeline.transcribe import parse_daic_transcript  # noqa: E402
from scripts.extract_acoustic import extract as extract_numpy  # noqa: E402
from scripts.extract_acoustic import read_wav  # noqa: E402

DEFAULT_ROOT = Path("E:/Create/daic_woz_data")
DEFAULT_LABELS = Path("E:/Create/full_split.csv")
DEFAULT_OUT = Path("data/private/real_features.csv")

ID_ALIASES = ("Participant_ID", "participant_id", "ParticipantId", "id")
SCORE_ALIASES = ("PHQ_Score", "phq8_score", "PHQ8_Score")
BINARY_ALIASES = ("PHQ_Binary", "phq8_binary", "PHQ8_Binary")


def pick(columns, aliases, label):
    lowered = {str(c).strip().lower(): c for c in columns}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    raise SystemExit(f"标签文件缺少{label}列，现有列: {list(columns)}")


def load_labels(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    id_col = pick(frame.columns, ID_ALIASES, " ID ")
    score_col = pick(frame.columns, SCORE_ALIASES, " PHQ 分数 ")
    binary_col = pick(frame.columns, BINARY_ALIASES, "二分类")
    return pd.DataFrame(
        {
            "participant_id": frame[id_col].astype(str).str.strip(),
            "phq8_score": pd.to_numeric(frame[score_col], errors="coerce"),
            "phq8_binary": pd.to_numeric(frame[binary_col], errors="coerce"),
        }
    ).dropna()


def safe_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.apply(pd.to_numeric, errors="coerce")


def acoustic_from_egemaps(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path, sep=";")
    required = (
        "F0semitoneFrom27.5Hz_sma3nz",
        "jitterLocal_sma3nz",
        "shimmerLocaldB_sma3nz",
        "Loudness_sma3",
    )
    if any(column not in frame.columns for column in required):
        return {}

    f0 = pd.to_numeric(frame["F0semitoneFrom27.5Hz_sma3nz"], errors="coerce")
    voiced = f0 > 0
    if not bool(voiced.any()):
        return {}

    f0_hz = 27.5 * np.power(2.0, f0[voiced].to_numpy(dtype=float) / 12.0)

    loudness = pd.to_numeric(frame["Loudness_sma3"], errors="coerce")
    span = float(loudness.max() - loudness.min())
    energy = (loudness - loudness.min()) / (span if span > 1e-6 else 1.0)

    jitter = pd.to_numeric(frame["jitterLocal_sma3nz"], errors="coerce")
    jitter = jitter[jitter > 0]
    shimmer = pd.to_numeric(frame["shimmerLocaldB_sma3nz"], errors="coerce")
    shimmer = shimmer[shimmer > 0]

    return {
        "f0_mean": float(np.mean(f0_hz)),
        "f0_std": float(np.std(f0_hz)),
        "energy_mean": float(np.mean(energy[voiced])),
        "speech_rate": float(voiced.mean() * 100 / 6),
        "pause_ratio": float(1.0 - voiced.mean()),
        "jitter": float(np.mean(jitter)) if len(jitter) else 0.012,
        "shimmer": float(min(np.mean(shimmer) / 10.0, 0.2)) if len(shimmer) else 0.055,
    }


def visual_from_openface(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path)
    au_columns = [c for c in frame.columns if c.startswith("AU") and c.endswith("_r")]
    if not au_columns:
        return {}

    au = safe_numeric(frame[au_columns])
    gaze = pd.to_numeric(frame["gaze_angle_y"], errors="coerce") if "gaze_angle_y" in frame.columns else None
    smile = pd.to_numeric(frame["AU12_r"], errors="coerce") if "AU12_r" in frame.columns else None
    pose_columns = [c for c in ("pose_Rx", "pose_Ry", "pose_Rz") if c in frame.columns]
    pose = safe_numeric(frame[pose_columns]) if pose_columns else None

    return {
        "au_intensity_mean": float(au.mean().mean()),
        "au_intensity_std": float(au.std().mean()),
        "gaze_away_ratio": float((gaze.abs() > 0.3).mean()) if gaze is not None else 0.32,
        "smile_freq": float((smile > 0.5).mean()) if smile is not None else 0.20,
        "head_motion": float(pose.std().mean()) if pose is not None else 0.30,
    }


def build_one(directory: Path, max_seconds: float):
    participant = directory.name.split("_")[0]
    features_dir = directory / "features"

    transcripts = list(directory.glob("*_Transcript.csv")) + list(directory.glob("*_TRANSCRIPT.csv"))
    text = parse_daic_transcript(transcripts[0].read_bytes()) if transcripts else ""
    text_features = extract_text_features(text)

    acoustic: dict[str, float] = {}
    visual: dict[str, float] = {}
    source = "fallback"

    if features_dir.exists():
        egemaps = next(
            (path for path in features_dir.glob("*egemaps*.csv") if "BoAW" not in path.name),
            None,
        )
        if egemaps is not None:
            try:
                acoustic = acoustic_from_egemaps(egemaps)
                if acoustic:
                    source = "egemaps"
            except Exception:
                acoustic = {}

        openface = next(
            (path for path in features_dir.glob("*Pose_gaze*.csv") if "BoVW" not in path.name),
            None,
        )
        if openface is not None:
            try:
                visual = visual_from_openface(openface)
            except Exception:
                visual = {}

    if not acoustic:
        audios = list(directory.glob("*_AUDIO.wav"))
        if audios:
            try:
                signal, rate = read_wav(audios[0], max_seconds)
                acoustic = extract_numpy(signal, rate)
            except Exception:
                acoustic = {}

    merged = merge_features(text_features, acoustic=acoustic, visual=visual)
    return participant, merged, bool(text), bool(acoustic), bool(visual), source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not args.root.exists():
        raise SystemExit(f"数据目录不存在: {args.root}")
    if not args.labels.exists():
        raise SystemExit(f"标签文件不存在: {args.labels}")

    labels = load_labels(args.labels)
    label_map = labels.set_index("participant_id")

    directories = sorted([p for p in args.root.iterdir() if p.is_dir()], key=lambda p: p.name)
    if args.limit:
        directories = directories[: args.limit]

    rows = []
    missing_label = 0
    egemaps_count = 0
    visual_count = 0

    for index, directory in enumerate(directories, start=1):
        participant, features, has_text, has_acoustic, has_visual, source = build_one(
            directory, args.max_seconds
        )
        if participant not in label_map.index:
            missing_label += 1
            continue
        if source == "egemaps":
            egemaps_count += 1
        if has_visual:
            visual_count += 1

        row = {"participant_id": participant}
        row.update({name: features[name] for name in FEATURE_NAMES})
        row["phq8_score"] = float(label_map.loc[participant, "phq8_score"])
        row["phq8_binary"] = int(label_map.loc[participant, "phq8_binary"])
        rows.append(row)

        if index % 10 == 0:
            print(f"[{index}/{len(directories)}] 已处理 {len(rows)} 条")

    if not rows:
        raise SystemExit("没有生成任何样本：请检查标签 ID 与目录名是否一致")

    frame = pd.DataFrame(rows)
    frame = frame[["participant_id", "phq8_score", "phq8_binary", *FEATURE_NAMES]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)

    print("=" * 62)
    print(f"输出: {args.out}")
    print(f"样本数: {len(frame)}")
    print(f"使用 eGeMAPS 声学: {egemaps_count}")
    print(f"使用 OpenFace 视觉: {visual_count}")
    print(f"缺少标签跳过: {missing_label}")
    print(f"抑郁比例: {frame['phq8_binary'].mean():.1%}")
    print(f"分数范围: [{frame['phq8_score'].min():.0f}, {frame['phq8_score'].max():.0f}]")
    print("=" * 62)
    print("各特征均值:")
    print(frame[list(FEATURE_NAMES)].mean().round(4).to_string())


if __name__ == "__main__":
    main()