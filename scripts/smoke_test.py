"""部署后冒烟测试：验证健康检查、示例分析与文本分析三个接口。

用法：
    # 服务已在运行
    python scripts/smoke_test.py --base-url http://127.0.0.1:8000

    # 由脚本自行拉起本地服务（部署自检推荐）
    python scripts/smoke_test.py --spawn --port 8012
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent

SAMPLE_TEXT = "最近一直失眠，什么都不想做，很累，注意力集中不了，饭也吃不下。"


def wait_until_ready(base_url: str, timeout: float = 90.0) -> httpx.Response:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/api/v1/health", timeout=5.0)
            if response.status_code == 200:
                return response
        except Exception as exc:
            last_error = exc
        time.sleep(2.0)
    raise RuntimeError(f"服务在 {timeout:.0f}s 内未就绪，最后一次错误: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8012")
    parser.add_argument("--spawn", action="store_true")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()

    process: subprocess.Popen | None = None
    base_url = args.base_url

    if args.spawn:
        base_url = f"http://127.0.0.1:{args.port}"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    try:
        health = wait_until_ready(base_url)
        body = health.json()
        print(f"[ok] health status={body['status']} model_loaded={body['model_loaded']}")

        demo = httpx.post(f"{base_url}/api/v1/demo", timeout=60.0)
        demo.raise_for_status()
        demo_body = demo.json()
        print(
            f"[ok] demo score={demo_body['phq8_score_estimation']} "
            f"risk={demo_body['risk_level']} evidence={len(demo_body['evidence'])}"
        )

        analyze = httpx.post(
            f"{base_url}/api/v1/analyze",
            data={"transcript": SAMPLE_TEXT, "participant_id": "smoke"},
            timeout=60.0,
        )
        analyze.raise_for_status()
        analyze_body = analyze.json()
        print(
            f"[ok] analyze score={analyze_body['phq8_score_estimation']} "
            f"risk={analyze_body['risk_level']} "
            f"backend={analyze_body['llm_backend']}"
        )
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    print("smoke test passed")


if __name__ == "__main__":
    main()
