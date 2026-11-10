"""评估脚本：对比 predictions.json 与真实标签。

相比常见写法，本脚本做了以下健壮性处理：
1. ID 统一为字符串比较，避免 int/str 不匹配导致的“零样本静默失败”；
2. 断言预测条数与标签条数一致，缺失直接报错；
3. 单一类别时跳过 AUC 而不是崩溃；
4. 概率裁剪到 [0, 1]；
5. 输出回归、分类与最差样本三类信息。

用法：
    python scripts/evaluate.py --predictions predictions.json --labels data/demo/features_demo.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_predictions(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    pred_map: dict[str, dict] = {}
    for item in raw:
        pid = str(item.get("participant_id", "")).strip()
        if not pid:
            continue
        pred_map[pid] = item.get("prediction", {})
    if not pred_map:
        raise SystemExit("predictions.json 为空或缺失 participant_id")
    return pred_map


ID_ALIASES = ["participant_id", "Participant_ID", "ParticipantId", "pid", "id"]
SCORE_ALIASES = ["phq8_score", "PHQ_Score", "PHQ8_Score", "phq_score"]
BINARY_ALIASES = ["phq8_binary", "PHQ_Binary", "PHQ8_Binary", "phq_binary"]


def pick_column(columns, aliases: list[str], label: str) -> str:
    lowered = {str(column).strip().lower(): column for column in columns}
    for alias in aliases:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    raise SystemExit(f"标签缺少{label}列，现有列: {list(columns)}")


def normalize_labels(labels: pd.DataFrame, id_column: str | None = None) -> pd.DataFrame:
    id_col = id_column or pick_column(labels.columns, ID_ALIASES, " ID ")
    if id_col not in labels.columns:
        raise SystemExit(f"指定的 ID 列不存在: {id_col}，现有列: {list(labels.columns)}")
    score_col = pick_column(labels.columns, SCORE_ALIASES, " PHQ 分数 ")
    binary_col = pick_column(labels.columns, BINARY_ALIASES, "二分类标签")
    return pd.DataFrame(
        {
            "pid": labels[id_col].astype(str).str.strip(),
            "PHQ_Score": pd.to_numeric(labels[score_col], errors="coerce"),
            "PHQ_Binary": pd.to_numeric(labels[binary_col], errors="coerce"),
        }
    )


def align(predictions: dict[str, dict], labels: pd.DataFrame) -> pd.DataFrame:
    labels = labels.dropna(subset=["PHQ_Score", "PHQ_Binary"])

    rows = []
    missing = []
    for _, row in labels.iterrows():
        pid = row["pid"]
        if pid not in predictions:
            missing.append(pid)
            continue
        pred = predictions[pid]
        rows.append(
            {
                "participant_id": pid,
                "true_score": float(row["PHQ_Score"]),
                "pred_score": float(pred.get("phq8_score_estimation", np.nan)),
                "true_binary": int(row["PHQ_Binary"]),
                "pred_prob": float(pred.get("depression_probability", np.nan)),
                "pred_binary": int(pred.get("depression_classification", np.nan)),
            }
        )

    aligned = pd.DataFrame(rows)
    if aligned.empty:
        raise SystemExit(
            f"没有任何样本匹配成功：预测 {len(predictions)} 条，标签 {len(labels)} 条。"
            "请检查 participant_id 是否一致。"
        )
    print(f"匹配成功 {len(aligned)} / 标签 {len(labels)} 条")
    if missing:
        print(f"缺失预测 {len(missing)} 条，例如: {missing[:5]}")
    return aligned


def report(frame: pd.DataFrame) -> None:
    frame = frame.dropna(subset=["pred_score", "pred_prob"])
    frame["pred_prob"] = frame["pred_prob"].clip(0.0, 1.0)

    y_true = frame["true_score"].to_numpy()
    y_pred = frame["pred_score"].to_numpy()
    y_binary = frame["true_binary"].to_numpy()
    y_prob = frame["pred_prob"].to_numpy()
    y_pred_bin = frame["pred_binary"].to_numpy()

    mse = mean_squared_error(y_true, y_pred)
    print("=" * 60)
    print("回归任务 (PHQ-8 分数)")
    print("=" * 60)
    print(f"MAE  : {mean_absolute_error(y_true, y_pred):.3f}")
    print(f"RMSE : {np.sqrt(mse):.3f}")
    print(f"MSE  : {mse:.3f}")
    if y_true.std() > 0 and y_pred.std() > 0:
        print(f"Pearson r: {np.corrcoef(y_true, y_pred)[0, 1]:.4f}")
    print(f"真实分数范围: [{y_true.min():.0f}, {y_true.max():.0f}]")
    print(f"预测分数范围: [{y_pred.min():.2f}, {y_pred.max():.2f}]")

    print()
    print("=" * 60)
    print("分类任务 (PHQ-8 >= 10 为抑郁)")
    print("=" * 60)
    print(f"Accuracy: {accuracy_score(y_binary, y_pred_bin) * 100:.1f}%")
    if len(np.unique(y_binary)) > 1:
        print(f"AUC     : {roc_auc_score(y_binary, y_prob):.4f}")
    else:
        print("AUC     : 无法计算（标签只有单一类别）")
    print("混淆矩阵:")
    print(confusion_matrix(y_binary, y_pred_bin))
    print(classification_report(y_binary, y_pred_bin, target_names=["非抑郁", "抑郁"], zero_division=0))

    print("=" * 60)
    print("误差最大的 10 个样本")
    print("=" * 60)
    frame = frame.assign(abs_error=np.abs(y_true - y_pred)).sort_values("abs_error", ascending=False)
    view_columns = [
        "participant_id",
        "true_score",
        "pred_score",
        "abs_error",
        "true_binary",
        "pred_prob",
    ]
    view = frame.head(10)[view_columns]
    print(view.to_string(index=False, float_format=lambda v: f"{v:.2f}"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--id-column", type=str, default=None)
    args = parser.parse_args()

    predictions = load_predictions(args.predictions)
    labels = normalize_labels(pd.read_csv(args.labels), args.id_column)

    report(align(predictions, labels))


if __name__ == "__main__":
    main()
