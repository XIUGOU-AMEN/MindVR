import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session", autouse=True)
def ensure_artifacts() -> None:
    demo = ROOT / "data" / "demo" / "features_demo.csv"
    model = ROOT / "models" / "phq8_model.joblib"

    if not demo.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_demo_data.py")],
            cwd=ROOT,
            check=True,
        )
    if not model.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "train.py"), "--no-cv"],
            cwd=ROOT,
            check=True,
        )
