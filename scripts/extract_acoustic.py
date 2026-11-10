"""从 wav 本地提取声学特征，输出与 backend.pipeline.features 对齐的 JSON。

不依赖 openSMILE / ffmpeg，只用标准库 wave + numpy，装好依赖即可运行。

用法：
    python scripts/extract_acoustic.py --participant 300
    python scripts/extract_acoustic.py --file "E:/Create/daic_woz_data/300_P/300_AUDIO.wav"
    python scripts/extract_acoustic.py --participant 300 --max-seconds 180 --out data/private/300.json
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_ROOT = Path("E:/Create/daic_woz_data")
DEFAULT_OUT = Path("data/private")

FEATURE_KEYS = (
    "f0_mean",
    "f0_std",
    "energy_mean",
    "speech_rate",
    "pause_ratio",
    "jitter",
    "shimmer",
)


def find_audio(root: Path, participant: str) -> Path | None:
    for pattern in (f"{participant}_P/*_AUDIO.wav", f"*{participant}*_AUDIO.wav"):
        for candidate in root.rglob(pattern):
            if candidate.is_file():
                return candidate
    return None


def read_wav(path: Path, max_seconds: float) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        width = source.getsampwidth()
        rate = source.getframerate()
        frame_count = source.getnframes()
        limit = int(min(frame_count, rate * max_seconds))
        raw = source.readframes(limit)

    if width != 2:
        raise SystemExit("仅支持 16-bit PCM wav")

    signal = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if channels > 1:
        signal = signal.reshape(-1, channels).mean(axis=1)
    return signal, rate


def frame_signal(signal: np.ndarray, rate: int, frame_ms: float = 40, hop_ms: float = 20) -> np.ndarray:
    frame_len = int(rate * frame_ms / 1000)
    hop = int(rate * hop_ms / 1000)
    if len(signal) < frame_len:
        return np.zeros((0, frame_len), dtype=np.float32)
    count = 1 + (len(signal) - frame_len) // hop
    indices = np.arange(frame_len)[None, :] + hop * np.arange(count)[:, None]
    return signal[indices]


def estimate_f0(frames: np.ndarray, rate: int, limit: int = 400) -> np.ndarray:
    """自相关法估计基频，只取能量最高的若干帧，避免全量计算过慢。"""
    if frames.shape[0] == 0:
        return np.zeros(0, dtype=np.float32)

    energies = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-9)
    order = np.argsort(energies)[::-1][:limit]
    selected = frames[order]

    min_lag = max(2, int(rate / 400))
    max_lag = int(rate / 70)
    values: list[float] = []

    for frame in selected:
        if len(frame) <= max_lag:
            continue
        centered = frame - frame.mean()
        corr = np.correlate(centered, centered, mode="full")[len(centered) - 1 :]
        if corr[0] <= 0:
            continue
        window = corr[min_lag:max_lag]
        if window.size == 0:
            continue
        lag = int(np.argmax(window)) + min_lag
        if corr[lag] / corr[0] < 0.3:
            continue
        values.append(rate / lag)

    return np.array(values, dtype=np.float32)


def robust_relative_diff(values: np.ndarray) -> float:
    """用中位数差分估计 jitter/shimmer，避免单个跳变把结果拉爆。"""
    if values.size < 3:
        return 0.0
    diffs = np.abs(np.diff(values))
    base = float(np.median(values))
    if base <= 0:
        return 0.0
    return float(np.median(diffs) / base)


def extract(signal: np.ndarray, rate: int) -> dict[str, float]:
    frames = frame_signal(signal, rate)
    if frames.shape[0] == 0:
        raise SystemExit("音频太短，无法分帧")

    energy = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-9) / 32768.0
    peak_energy = float(energy.max()) or 1.0
    normalized_energy = energy / peak_energy

    threshold = max(float(np.percentile(normalized_energy, 60)) * 0.6, 0.01)
    voiced_mask = normalized_energy > threshold
    voiced_ratio = float(voiced_mask.mean())

    f0 = estimate_f0(frames[voiced_mask], rate)

    speech_rate = float(voiced_ratio * 100 / 6) if voiced_ratio > 0 else 3.0

    if f0.size > 1:
        f0_mean = float(np.median(f0))
        f0_std = float(np.std(f0))
        jitter = robust_relative_diff(f0)
    else:
        f0_mean = 145.0
        f0_std = 28.0
        jitter = 0.012

    shimmer = robust_relative_diff(energy)

    return {
        "f0_mean": round(f0_mean, 4),
        "f0_std": round(f0_std, 4),
        "energy_mean": round(float(np.mean(normalized_energy)), 4),
        "speech_rate": round(speech_rate, 4),
        "pause_ratio": round(1.0 - voiced_ratio, 4),
        "jitter": round(jitter, 4),
        "shimmer": round(min(shimmer, 0.4), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--participant", default=None)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.file is None:
        if not args.participant:
            raise SystemExit("请指定 --file 或 --participant")
        found = find_audio(args.root, args.participant)
        if found is None:
            raise SystemExit(f"在 {args.root} 下没有找到 {args.participant} 的 wav")
        args.file = found

    if not args.file.exists():
        raise SystemExit(f"文件不存在: {args.file}")

    signal, rate = read_wav(args.file, args.max_seconds)
    features = extract(signal, rate)

    print(f"文件: {args.file}")
    print(f"采样率: {rate} Hz | 分析时长: {len(signal) / rate:.1f} 秒")
    print(json.dumps(features, ensure_ascii=False, indent=2))

    out_path = args.out
    if out_path is None:
        name = f"{args.participant or args.file.stem}_acoustic.json"
        out_path = DEFAULT_OUT / name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(features, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存: {out_path}")


if __name__ == "__main__":
    main()