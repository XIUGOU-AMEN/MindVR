"""批量预测，输出与官方评测脚本兼容的 predictions.json。

用法：
    python scripts/predict.py --data data/demo/features_demo.csv --out predictions.json
    python scripts/predict.py --data demo.csv --transcript-column transcript --out predictions.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.features import FEATURE_NAMES, extract_text_features, merge_features  # noqa: E402
from backend.pipeline.regress import DepressionModel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "models" / "phq8_model.joblib"


def build_features(row: pd.Series, transcript_column: str | None) -> dict[str, float]:
    if transcript_column and transcript_column in row and pd.notna(row[transcript_column]):
        return merge_features(extract_text_features(str(row[transcript_column])))
    return {name: float(row[name]) for name in FEATURE_NAMES if name in row and pd.notna(row[name])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, default=ROOT / "predictions.json")
    parser.add_argument("--transcript-column", type=str, default=None)
    parser.add_argument("--id-column", type=str, default="participant_id")
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(f"模型不存在: {args.model}，请先运行 python scripts/train.py")

    frame = pd.read_csv(args.data)
    if args.id_column not in frame.columns:
        raise SystemExit(f"数据缺少 ID 列: {args.id_column}")

    model = DepressionModel.load(args.model)
    results = []
    for _, row in frame.iterrows():
        features = build_features(row, args.transcript_column)
        prediction = model.predict(features)
        results.append(
            {
                "participant_id": str(row[args.id_column]),
                "prediction": {
                    "phq8_score_estimation": prediction["phq8_score_estimation"],
                    "depression_probability": prediction["depression_probability"],
                    "depression_classification": prediction["depression_classification"],
                    "risk_level": prediction["risk_level"],
                },
            }
        )

    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)

    print(f"已生成 {len(results)} 条预测 -> {args.out}")


if __name__ == "__main__":
    main()
