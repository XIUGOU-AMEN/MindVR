"""把 DAIC-WOZ 的逐句转写文件批量转换为纯文本表。

用法：
    python scripts/extract_daic_transcripts.py --root "E:/Create/daic_woz_data"
    python scripts/extract_daic_transcripts.py --root "E:/Create/daic_woz_data" --out data/raw/transcripts.csv
    python scripts/extract_daic_transcripts.py --single "E:/Create/daic_woz_data/300_P/300_Transcript.csv"

输出列：participant_id, transcript, n_words, n_utterances, source_file
默认输出到 data/raw/transcripts.csv（该目录已被 .gitignore 忽略）。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.transcribe import parse_daic_transcript  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "raw" / "transcripts.csv"

TRANSCRIPT_PATTERNS = ("*_transcript.csv", "*_transcript.tsv", "*Transcript.csv")
ID_PATTERN = re.compile(r"(\d{3,4})")


def find_transcripts(root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in TRANSCRIPT_PATTERNS:
        found.extend(root.rglob(pattern))
    unique = {path.resolve(): path for path in found}
    return sorted(unique.values(), key=lambda path: str(path))


def participant_id(path: Path) -> str:
    match = ID_PATTERN.search(path.stem)
    if match:
        return match.group(1)
    return path.parent.name


def count_utterances(text: str) -> int:
    return max(1, len(re.split(r"[.?!。！？]", text)) - 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("E:/Create/daic_woz_data"))
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--single", type=Path, default=None)
    args = parser.parse_args()

    if args.single:
        text = parse_daic_transcript(args.single.read_bytes())
        print(f"participant={participant_id(args.single)} words={len(text.split())}")
        print(text)
        return

    if not args.root.exists():
        raise SystemExit(f"数据目录不存在: {args.root}")

    files = find_transcripts(args.root)
    if not files:
        raise SystemExit(f"在 {args.root} 下没有找到转写文件")

    rows = []
    for path in files:
        try:
            text = parse_daic_transcript(path.read_bytes())
        except Exception as exc:
            print(f"[skip] {path}: {exc}")
            continue
        if not text:
            print(f"[skip] {path}: 解析结果为空")
            continue
        rows.append(
            {
                "participant_id": participant_id(path),
                "transcript": text,
                "n_words": len(text.split()),
                "n_utterances": count_utterances(text),
                "source_file": str(path),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"已解析 {len(rows)} 条转写 -> {args.out}")
    if rows:
        avg_words = sum(row["n_words"] for row in rows) / len(rows)
        print(f"平均词数: {avg_words:.0f}")


if __name__ == "__main__":
    main()
