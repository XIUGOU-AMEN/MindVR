"""API 数据契约。字段名与官方评测脚本 predictions.json 保持一致，便于复用既有指标代码。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["normal", "mild", "moderate", "severe"]


class BaseSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class EvidenceItem(BaseSchema):
    feature: str
    label_zh: str
    value: float
    contribution: float
    direction: Literal["up", "down"]


class AnalysisResult(BaseSchema):
    participant_id: str
    phq8_score_estimation: float = Field(ge=0, le=24)
    depression_probability: float = Field(ge=0.0, le=1.0)
    depression_classification: int = Field(ge=0, le=1)
    risk_level: RiskLevel
    evidence: list[EvidenceItem] = Field(default_factory=list)
    transcript_excerpt: str = ""
    model_version: str = ""
    llm_backend: str = ""
    latency_ms: int = 0


class AnalysisRequest(BaseSchema):
    participant_id: str = "anonymous"
    transcript: str = ""
    features: dict[str, float] = Field(default_factory=dict)


class JobRecord(BaseSchema):
    job_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    created_at: datetime
    error: str | None = None
    result: AnalysisResult | None = None


class HealthResponse(BaseSchema):
    status: str
    version: str
    llm_backend: str
    model_loaded: bool
    asr_enabled: bool = False


class ModelInfo(BaseSchema):
    model_version: str
    pipeline: str
    n_features: int
    feature_names: list[str]
    binary_threshold: int
