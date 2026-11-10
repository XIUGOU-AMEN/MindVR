from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.pipeline.features import FEATURE_NAMES
from backend.pipeline.regress import DepressionModel, risk_level

ROOT = Path(__file__).resolve().parent.parent


def load_demo() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "demo" / "features_demo.csv")


def test_risk_level_boundaries() -> None:
    assert risk_level(0) == "normal"
    assert risk_level(4.9) == "normal"
    assert risk_level(5) == "mild"
    assert risk_level(9.9) == "mild"
    assert risk_level(10) == "moderate"
    assert risk_level(15) == "severe"


def test_fit_and_predict_ranges() -> None:
    frame = load_demo()
    X = frame[FEATURE_NAMES].to_numpy(dtype=np.float64)
    model = DepressionModel().fit(
        X,
        frame["phq8_score"].to_numpy(dtype=np.float64),
        frame["phq8_binary"].to_numpy(dtype=np.int64),
    )

    features = dict(zip(FEATURE_NAMES, X[0]))
    prediction = model.predict(features)

    assert 0.0 <= prediction["phq8_score_estimation"] <= 24.0
    assert 0.0 <= prediction["depression_probability"] <= 1.0
    assert prediction["depression_classification"] in (0, 1)
    assert prediction["risk_level"] in {"normal", "mild", "moderate", "severe"}
    assert prediction["evidence"]


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    frame = load_demo()
    X = frame[FEATURE_NAMES].to_numpy(dtype=np.float64)
    model = DepressionModel().fit(
        X,
        frame["phq8_score"].to_numpy(dtype=np.float64),
        frame["phq8_binary"].to_numpy(dtype=np.int64),
    )
    path = model.save(tmp_path / "model.joblib")
    loaded = DepressionModel.load(path)

    features = dict(zip(FEATURE_NAMES, X[3]))
    a = model.predict(features)
    b = loaded.predict(features)
    assert a["phq8_score_estimation"] == pytest.approx(b["phq8_score_estimation"])
    assert a["depression_probability"] == pytest.approx(b["depression_probability"])


def test_single_class_training_rejected() -> None:
    frame = load_demo()
    X = frame[FEATURE_NAMES].to_numpy(dtype=np.float64)
    labels = np.zeros(len(frame), dtype=np.int64)
    with pytest.raises(ValueError):
        DepressionModel().fit(X, frame["phq8_score"].to_numpy(dtype=np.float64), labels)
