"""用「转写文本 + 声学特征 JSON」跑一次多模态分析。

用于验证本地声学特征确实参与了融合，不经过 HTTP。

用法：
    python scripts/analyze_multimodal.py --participant 300
    python scripts/analyze_multimodal.py --participant 300 --acoustic data/private/300_acoustic.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.orchestrator import analyze_features  # noqa: E402
from backend.pipeline.transcribe import parse_daic_transcript  # noqa: E402

DEFAULT_ROOT = Path("E:/Create/daic_woz_data")


def find_transcript(root: Path, participant: str) -> Path | None:
    for pattern in (
        f"{participant}_P/*_Transcript.csv",
        f"{participant}_P/*_TRANSCRIPT.csv",
        f"*{participant}*_Transcript.csv",
    ):
        for candidate in root.rglob(pattern):
            if candidate.is_file():
                return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", default="300")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--transcript", type=Path, default=None)
    parser.add_argument("--acoustic", type=Path, default=None)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    transcript_path = args.transcript or find_transcript(args.root, args.participant)
    if transcript_path is None or not transcript_path.exists():
        raise SystemExit(f"没有找到 {args.participant} 的转写文件")

    text = parse_daic_transcript(transcript_path.read_bytes())
    if not text:
        raise SystemExit("转写解析结果为空")

    acoustic_path = args.acoustic
    if acoustic_path is not None and not acoustic_path.exists():
        raise SystemExit(f"声学文件不存在: {acoustic_path}")

    result = analyze_features(
        participant_id=args.participant,
        transcript=text,
        acoustic_path=str(acoustic_path) if acoustic_path else None,
        use_llm=not args.no_llm,
    )

    print(f"转写: {transcript_path}")
    print(f"声学: {acoustic_path or '未提供（使用群体中位数）'}")
    print(f"词数: {len(text.split())}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()