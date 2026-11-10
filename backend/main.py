"""FastAPI 入口。"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.cache import cache
from backend.config import get_settings
from backend.db import AnalysisRecord, SessionLocal, init_db
from backend.llm.factory import build_backend
from backend.pipeline.orchestrator import analyze_features, get_model
from backend.pipeline.transcribe import (
    get_transcriber,
    looks_like_transcript_content,
    looks_like_transcript_file,
    parse_daic_transcript,
)
from backend.schemas import AnalysisResult, HealthResponse, ModelInfo

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="MindVR API", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        llm_backend=build_backend().name,
        model_loaded=get_model() is not None,
        asr_enabled=settings.use_cloud_asr,
    )


@app.get("/api/v1/model/info", response_model=ModelInfo)
def model_info() -> ModelInfo:
    model = get_model()
    if model is None:
        raise HTTPException(status_code=503, detail="模型未加载，请先运行 scripts/train.py")
    return ModelInfo(**model.info())


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze(
    transcript: str = Form(default=""),
    participant_id: str = Form(default="anonymous"),
    audio: UploadFile | None = File(default=None),
) -> AnalysisResult:
    text = transcript.strip()
    if text and looks_like_transcript_content(text):
        text = parse_daic_transcript(text)
    if not text and audio is not None:
        raw = await audio.read()
        if looks_like_transcript_file(audio.filename or ""):
            text = parse_daic_transcript(raw)
        else:
            text = get_transcriber().transcribe(raw)
    if not text:
        raise HTTPException(
            status_code=400,
            detail=(
                "没有可分析的文本：请粘贴访谈文本、上传 DAIC 转写 CSV，"
                "或开启 USE_CLOUD_ASR 后上传音频"
            ),
        )

    try:
        result = analyze_features(participant_id=participant_id, transcript=text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload = AnalysisResult(**result)
    persist(payload)
    return payload


@app.post("/api/v1/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    """只做语音转写，返回文本，便于单独验证 SIS 链路。"""
    raw = await audio.read()
    transcriber = get_transcriber()
    try:
        text = transcriber.transcribe(raw)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not text:
        raise HTTPException(
            status_code=400,
            detail="转写结果为空：请确认 USE_CLOUD_ASR=true、AK/SK 已配置、音频为 16k/8k wav",
        )

    return {
        "transcript": text,
        "characters": len(text),
        "backend": transcriber.name,
        "chunks": getattr(transcriber, "last_chunks", 0),
        "failed_chunks": getattr(transcriber, "last_failed", 0),
    }


@app.post("/api/v1/demo", response_model=AnalysisResult)
def demo() -> AnalysisResult:
    sample = (
        "最近一直睡不好，晚上两三点就醒了。以前喜欢打球，现在完全没兴趣，什么都不想做。"
        "总觉得很累，脑子也转不动，工作老是走神。我觉得自己挺没用的，对不起家里人。"
    )
    try:
        result = analyze_features(participant_id="demo", transcript=sample, use_llm=False)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    payload = AnalysisResult(**result)
    cache.set_json(f"result:{uuid.uuid4()}", payload.model_dump())
    return payload


def persist(result: AnalysisResult) -> None:
    job_id = uuid.uuid4().hex
    record = AnalysisRecord(
        job_id=job_id,
        participant_id=result.participant_id,
        phq8_score=result.phq8_score_estimation,
        probability=result.depression_probability,
        classification=result.depression_classification,
        risk_level=result.risk_level,
        evidence_json=json.dumps([e.model_dump() for e in result.evidence], ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
    )
    with SessionLocal() as session:
        session.add(record)
        session.commit()
