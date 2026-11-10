"""HTTP 层测试。

默认跳过：部分受限环境（如本机沙箱）禁止事件循环创建 self-pipe，
会让异步 HTTP 测试报 WinError 10051。在正常开发机或 CI 中设置
MINDVR_HTTP_TESTS=1 即可运行。
"""

from __future__ import annotations

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db import init_db
from backend.main import app

RUN_HTTP = os.environ.get("MINDVR_HTTP_TESTS", "").lower() in {"1", "true", "yes"}

pytestmark = pytest.mark.skipif(
    not RUN_HTTP,
    reason="设置 MINDVR_HTTP_TESTS=1 以运行 HTTP 层测试",
)

SAMPLE_TRANSCRIPT_CSV = (
    "Start_Time,End_Time,Text,Confidence\n"
    "1.0,2.0,I can't sleep at night,0.95\n"
    "2.5,3.5,I have no interest in anything,0.90\n"
    "4.0,5.0,I feel tired and I can't focus,0.92\n"
)


def request(method: str, url: str, **kwargs):
    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_call())


def test_health_endpoint() -> None:
    init_db()
    response = request("GET", "/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_requires_text_or_audio() -> None:
    init_db()
    response = request("POST", "/api/v1/analyze", data={"transcript": ""})
    assert response.status_code == 400


def test_analyze_accepts_transcript_csv_upload() -> None:
    init_db()
    response = request(
        "POST",
        "/api/v1/analyze",
        data={"participant_id": "300"},
        files={
            "audio": (
                "300_Transcript.csv",
                SAMPLE_TRANSCRIPT_CSV.encode("utf-8"),
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["participant_id"] == "300"
    assert body["evidence"]
