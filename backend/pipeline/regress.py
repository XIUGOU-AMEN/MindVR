"""PHQ-8 回归与抑郁二分类模型。

设计要点：大模型只负责从文本中抽取语义线索，分数由轻量监督模型给出。
这样既避免了大模型直接回归造成的“分数坍缩”，也让模型可在 CPU 上快速复现。
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.pipeline.features import (
    FEATURE_LABELS,
    FEATURE_NAMES,
    to_vector,
)

PHQ8_MIN = 0.0
PHQ8_MAX = 24.0


def risk_level(score: float) -> str:
    if score < 5:
        return "normal"
    if score < 10:
        return "mild"
    if score < 15:
        return "moderate"
    return "severe"


class DepressionModel:
    def __init__(self, binary_threshold: int = 10) -> None:
        self.binary_threshold = binary_threshold
        self.version = "phq8-gbdt-v1"
        self.trained_at: str = ""
        self.regressor = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "reg",
                    GradientBoostingRegressor(
                        n_estimators=200,
                        learning_rate=0.05,
                        max_depth=3,
                        subsample=0.9,
                        random_state=42,
                    ),
                ),
            ]
        )
        self.classifier = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        )

    def fit(self, X: np.ndarray, y_score: np.ndarray, y_binary: np.ndarray) -> "DepressionModel":
        self.regressor.fit(X, y_score)
        if len(np.unique(y_binary)) < 2:
            raise ValueError("训练集只有单一类别，无法训练分类器")
        self.classifier.fit(X, y_binary)
        self.trained_at = datetime.now(timezone.utc).isoformat()
        return self

    def predict(self, features: dict[str, float]) -> dict:
        X = to_vector(features)
        raw_score = float(self.regressor.predict(X)[0])
        score = float(np.clip(raw_score, PHQ8_MIN, PHQ8_MAX))
        probability = 1.0 / (1.0 + math.exp(-(score - self.binary_threshold) / 2.0))
        probability = float(np.clip(probability, 0.0, 1.0))
        classification = int(score >= self.binary_threshold)

        return {
            "phq8_score_estimation": round(score, 2),
            "depression_probability": round(probability, 4),
            "depression_classification": classification,
            "risk_level": risk_level(score),
            "evidence": self._attribute(X, features),
        }

    def _attribute(self, X: np.ndarray, features: dict[str, float], top_k: int = 6) -> list[dict]:
        """基于标准化后的线性分类器系数做近似归因，可解释且无需额外依赖。"""
        try:
            scaler: StandardScaler = self.classifier.named_steps["scaler"]
            clf: LogisticRegression = self.classifier.named_steps["clf"]
            z = scaler.transform(X)[0]
            contributions = z * clf.coef_[0]
        except Exception:
            return []

        order = np.argsort(np.abs(contributions))[::-1][:top_k]
        items = []
        for idx in order:
            name = FEATURE_NAMES[idx]
            items.append(
                {
                    "feature": name,
                    "label_zh": FEATURE_LABELS.get(name, name),
                    "value": round(float(features.get(name, 0.0)), 4),
                    "contribution": round(float(contributions[idx]), 4),
                    "direction": "up" if contributions[idx] >= 0 else "down",
                }
            )
        return items

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "regressor": self.regressor,
                "classifier": self.classifier,
                "version": self.version,
                "trained_at": self.trained_at,
                "binary_threshold": self.binary_threshold,
            },
            target,
        )
        return target

    @classmethod
    def load(cls, path: str | Path) -> "DepressionModel":
        data = joblib.load(Path(path))
        model = cls(binary_threshold=int(data.get("binary_threshold", 10)))
        model.regressor = data["regressor"]
        model.classifier = data["classifier"]
        model.version = data.get("version", model.version)
        model.trained_at = data.get("trained_at", "")
        return model

    def info(self) -> dict:
        return {
            "model_version": self.version,
            "pipeline": "StandardScaler + GradientBoostingRegressor / LogisticRegression",
            "n_features": len(FEATURE_NAMES),
            "feature_names": FEATURE_NAMES,
            "binary_threshold": self.binary_threshold,
        }
