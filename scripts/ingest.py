"""一键 ingest：上传一个 wav，自动完成转写 + 声学提取 + 风险评估。

设计目标：真实用户只需要给一段访谈录音，不需要准备 DAIC-WOZ 的 CSV。

处理流程：
    wav
      → 文本：优先使用同名/指定转写 CSV；否则调用 ASR（需 USE_CLOUD_ASR）
      → 声学：优先 openSMILE eGeMAPS（与数据集口径一致）；缺失时回退 numpy
      → 视觉：无视频，使用群体中位数，并在输出中标注
      → 融合 24 维 → PHQ-8 分数 + 风险等级 + 依据

用法：
    python scripts/ingest.py --audio "E:/Create/daic_woz_data/300_P/300_AUDIO.wav"
    python scripts/ingest.py --audio xxx.wav --transcript xxx_Transcript.csv
    python scripts/ingest.py --audio xxx.wav --no-llm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.orchestrator import analyze_features  # noqa: E402
from backend.pipeline.transcribe import get_transcriber, parse_daic_transcript  # noqa: E402
from scripts.extract_acoustic import extract as extract_numpy  # noqa: E402
from scripts.extract_acoustic import read_wav  # noqa: E402

DEFAULT_OUT = Path("data/private")


def acoustic_from_opensmile(path: Path) -> dict[str, float]:
    """用 openSMILE eGeMAPS Functionals 提取，口径与 DAIC 数据集一致。"""
    try:
        import opensmile
    except ImportError:
        return {}

    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    frame = smile.process_file(str(path))
    if frame is None or frame.empty:
        return {}

    row = frame.iloc[0]

    def read(name: str, default: float) -> float:
        try:
            value = float(row[name])
        except (KeyError, TypeError, ValueError):
            return default
        if value != value:
            return default
        return value

    f0_semitone = read("F0semitoneFrom27.5Hz_sma3nz_amean", 0.0)
    f0_mean = 27.5 * (2.0 ** (f0_semitone / 12.0)) if f0_semitone > 0 else 145.0
    f0_std_norm = read("F0semitoneFrom27.5Hz_sma3nz_stddevNorm", 0.0)
    f0_std = f0_mean * f0_std_norm if f0_std_norm > 0 else 28.0

    loudness_db = read("Loudness_sma3_amean", -60.0)
    energy_mean = min(1.0, max(0.0, (loudness_db + 60.0) / 60.0))

    segments = read("VoicedSegmentsPerSec", 3.0)
    mean_len = read("MeanVoicedSegmentLengthSec", 0.3)
    voiced_time = min(1.0, segments * mean_len)
    pause_ratio = 1.0 - voiced_time

    jitter = read("jitterLocal_sma3nz_amean", 0.012)
    shimmer_db = read("shimmerLocaldB_sma3nz_amean", 0.55)

    return {
        "f0_mean": round(f0_mean, 4),
        "f0_std": round(f0_std, 4),
        "energy_mean": round(energy_mean, 4),
        "speech_rate": round(segments, 4),
        "pause_ratio": round(max(0.0, pause_ratio), 4),
        "jitter": round(jitter, 4),
        "shimmer": round(min(max(shimmer_db / 10.0, 0.0), 0.2), 4),
    }


def acoustic_from_numpy(path: Path, max_seconds: float) -> dict[str, float]:
    signal, rate = read_wav(path, max_seconds)
    return extract_numpy(signal, rate)


def resolve_transcript(audio: Path, explicit: Path | None) -> tuple[str, str]:
    if explicit is not None:
        if not explicit.exists():
            raise SystemExit(f"转写文件不存在: {explicit}")
        if explicit.suffix.lower() in {".csv", ".tsv"}:
            return parse_daic_transcript(explicit.read_bytes()), f"csv:{explicit.name}"
        return explicit.read_text(encoding="utf-8", errors="ignore"), f"text:{explicit.name}"

    sibling = audio.with_name(audio.stem.replace("_AUDIO", "_Transcript") + ".csv")
    if sibling.exists():
        return parse_daic_transcript(sibling.read_bytes()), f"csv:{sibling.name}"

    transcriber = get_transcriber()
    if transcriber.name == "passthrough":
        raise SystemExit(
            "没有转写文件，且未开启云端 ASR。\n"
            "请加 --transcript 指定转写，或在 .env 设置 USE_CLOUD_ASR=true 并配置 SIS。"
        )
    return transcriber.transcribe(audio.read_bytes()), f"asr:{transcriber.name}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, default=None)
    parser.add_argument("--participant-id", default=None)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not args.audio.exists():
        raise SystemExit(f"音频不存在: {args.audio}")

    participant = args.participant_id or args.audio.stem.split("_")[0]

    text, text_source = resolve_transcript(args.audio, args.transcript)
    if not text.strip():
        raise SystemExit("转写结果为空，无法继续")

    acoustic = acoustic_from_opensmile(args.audio)
    acoustic_source = "opensmile"
    if not acoustic:
        acoustic = acoustic_from_numpy(args.audio, args.max_seconds)
        acoustic_source = "numpy"

    result = analyze_features(
        participant_id=participant,
        transcript=text,
        extra_features=acoustic,
        use_llm=not args.no_llm,
    )

    result["modalities"] = {
        "text": True,
        "acoustic": acoustic_source,
        "visual": "default（无视频输入）",
    }
    result["sources"] = {
        "audio": str(args.audio),
        "transcript": text_source,
    }

    print("=" * 62)
    print(f"音频: {args.audio}")
    print(f"文本来源: {text_source}")
    print(f"声学来源: {acoustic_source}")
    print(f"词数: {len(text.split())}")
    print("-" * 62)
    print("声学特征:")
    print(json.dumps(acoustic, ensure_ascii=False, indent=2))
    print("-" * 62)
    print("分析结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    out = args.out
    if out is None:
        DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
        out = DEFAULT_OUT / f"{participant}_ingest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()