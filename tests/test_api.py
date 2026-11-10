"""API 业务逻辑测试（同步直调，任何环境可运行）。"""

from __future__ import annotations

from backend.db import init_db
from backend.main import demo, health, model_info


def test_health_direct() -> None:
    init_db()
    result = health()
    assert result.status == "ok"
    assert result.model_loaded is True


def test_model_info_direct() -> None:
    init_db()
    info = model_info()
    assert info.n_features == 24
    assert len(info.feature_names) == 24


def test_demo_direct() -> None:
    init_db()
    result = demo()
    assert 0 <= result.phq8_score_estimation <= 24
    assert 0.0 <= result.depression_probability <= 1.0
    assert result.risk_level in {"normal", "mild", "moderate", "severe"}
    assert result.evidence
