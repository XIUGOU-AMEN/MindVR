"""训练 PHQ-8 回归与抑郁二分类模型。

用法：
    python scripts/train.py
    python scripts/train.py --data data/demo/features_demo.csv --out models/phq8_model.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.features import FEATURE_NAMES  # noqa: E402
from backend.pipeline.regress import DepressionModel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "demo" / "features_demo.csv"
DEFAULT_MODEL = ROOT / "models" / "phq8_model.joblib"


def load_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"未找到 {path}，自动生成合成数据 ...")
        from scripts.generate_demo_data import main as generate

        generate()
    frame = pd.read_csv(path)
    missing = [name for name in FEATURE_NAMES if name not in frame.columns]
    if missing:
        raise SystemExit(f"数据缺少特征列: {missing}")
    return frame


def cross_validate(X: np.ndarray, y_score: np.ndarray, y_binary: np.ndarray, folds: int) -> None:
    kf = KFold(n_splits=folds, shuffle=True, random_state=42)
    maes, aucs = [], []
    for train_idx, valid_idx in kf.split(X):
        model = DepressionModel()
        model.fit(X[train_idx], y_score[train_idx], y_binary[train_idx])
        pred_score = np.clip(model.regressor.predict(X[valid_idx]), 0, 24)
        maes.append(mean_absolute_error(y_score[valid_idx], pred_score))
        if len(np.unique(y_binary[valid_idx])) > 1:
            proba = model.classifier.predict_proba(X[valid_idx])[:, 1]
            aucs.append(roc_auc_score(y_binary[valid_idx], proba))
    print(f"{folds} 折交叉验证 MAE: {np.mean(maes):.3f} ± {np.std(maes):.3f}")
    if aucs:
        print(f"{folds} 折交叉验证 AUC: {np.mean(aucs):.4f} ± {np.std(aucs):.4f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--no-cv", action="store_true")
    args = parser.parse_args()

    frame = load_frame(args.data)
    X = frame[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_score = frame["phq8_score"].to_numpy(dtype=np.float64)
    y_binary = frame["phq8_binary"].to_numpy(dtype=np.int64)

    print(f"样本数 {len(frame)} | 抑郁比例 {y_binary.mean():.1%}")
    if not args.no_cv:
        cross_validate(X, y_score, y_binary, args.folds)

    model = DepressionModel()
    model.fit(X, y_score, y_binary)
    path = model.save(args.out)
    print(f"模型已保存 -> {path}")
    print(f"模型版本 {model.version} | 训练时间 {model.trained_at}")


if __name__ == "__main__":
    main()
