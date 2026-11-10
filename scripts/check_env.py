"""开发与部署环境自检。

用法：
    python scripts/check_env.py
    python scripts/check_env.py --cloud     # 同时检查华为云 SDK 与云端配置

退出码 0 表示必需项全部就绪；1 表示存在阻塞项。
"""

from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CORE_MODULES = {
    "fastapi": "FastAPI",
    "uvicorn": "Uvicorn",
    "pydantic": "Pydantic",
    "pydantic_settings": "pydantic-settings",
    "httpx": "HTTP 客户端",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "sklearn": "Scikit-learn",
    "joblib": "Joblib",
    "sqlalchemy": "SQLAlchemy",
    "redis": "Redis 客户端",
}

CLOUD_MODULES = {
    "obs": "华为云 OBS SDK",
    "huaweicloudsdkcore": "华为云 SDK Core",
    "huaweicloudsdksis": "华为云 SIS SDK",
}

REQUIRED_CLI = {
    "git": "版本控制（上传 Gitee/GitHub 必需）",
}

OPTIONAL_CLI = {
    "node": "前端构建（Web Demo / WebXR）",
    "npm": "前端依赖安装",
    "docker": "容器化部署（可选，也可直接 uvicorn 运行）",
}

status_ok = 0
status_warn = 0
status_fail = 0


def report(level: str, item: str, detail: str) -> None:
    global status_ok, status_warn, status_fail
    if level == "ok":
        status_ok += 1
        print(f"[ok]   {item}: {detail}")
    elif level == "warn":
        status_warn += 1
        print(f"[warn] {item}: {detail}")
    else:
        status_fail += 1
        print(f"[fail] {item}: {detail}")


def check_python() -> None:
    version = sys.version_info
    text = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 10):
        report("ok", "Python", text)
    else:
        report("fail", "Python", f"{text}，需要 3.10 及以上")


def check_modules(modules: dict[str, str], level: str) -> None:
    for name, label in modules.items():
        try:
            importlib.import_module(name)
        except Exception as exc:
            report(level, label, f"未安装或导入失败（{exc.__class__.__name__}）")
        else:
            report("ok", label, "可用")


def check_cli(tools: dict[str, str], level: str) -> None:
    for name, label in tools.items():
        path = shutil.which(name)
        if path:
            report("ok", label, path)
        else:
            report(level, label, "未找到可执行文件")


def check_files(use_cloud: bool) -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        report("ok", ".env", str(env_file))
        inspect_env(env_file, use_cloud)
    else:
        report("warn", ".env", "不存在，请复制 .env.example 后填写")

    model = ROOT / "models" / "phq8_model.joblib"
    if model.exists():
        report("ok", "模型文件", f"{model.name} ({model.stat().st_size // 1024} KB)")
    else:
        report("warn", "模型文件", "不存在，运行 python scripts/train.py")

    demo = ROOT / "data" / "demo" / "features_demo.csv"
    if demo.exists():
        report("ok", "演示数据", "data/demo/features_demo.csv")
    else:
        report("warn", "演示数据", "不存在，运行 python scripts/generate_demo_data.py")


def inspect_env(env_file: Path, use_cloud: bool) -> None:
    values: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    backend = values.get("LLM_BACKEND", "local")
    if backend == "maas":
        if values.get("MAAS_BASE_URL") and values.get("MAAS_API_KEY"):
            report("ok", "MaaS 配置", "已填写 endpoint 与 API Key")
        else:
            report("fail", "MaaS 配置", "LLM_BACKEND=maas 但 MAAS_BASE_URL / MAAS_API_KEY 为空")
    else:
        report("ok", "LLM 后端", f"{backend}（无需云端凭据）")

    if use_cloud:
        missing = [
            key
            for key in ("HUAWEI_AK", "HUAWEI_SK", "HUAWEI_PROJECT_ID", "OBS_BUCKET")
            if not values.get(key)
        ]
        if missing:
            report("warn", "华为云凭据", f"未填写: {', '.join(missing)}")
        else:
            report("ok", "华为云凭据", "AK/SK/ProjectId/Bucket 均已填写")

    db_url = values.get("DATABASE_URL", "sqlite:///./data/app.db")
    report("ok", "数据库", "SQLite（本地）" if db_url.startswith("sqlite") else "外部数据库（RDS 等）")
    report("ok", "Redis", values.get("REDIS_URL") or "未配置，自动使用内存缓存")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud", action="store_true", help="检查华为云 SDK 与凭据")
    args = parser.parse_args()

    print("=" * 66)
    print("MindVR 环境自检")
    print("=" * 66)

    check_python()
    check_modules(CORE_MODULES, "fail")
    if args.cloud:
        check_modules(CLOUD_MODULES, "warn")
    check_cli(REQUIRED_CLI, "fail")
    check_cli(OPTIONAL_CLI, "warn")
    check_files(args.cloud)

    print("-" * 66)
    print(f"通过 {status_ok} | 提醒 {status_warn} | 阻塞 {status_fail}")
    print("-" * 66)
    if status_fail:
        print("存在阻塞项，请先按提示处理。")
        raise SystemExit(1)

    print("必需项已就绪。下一步：")
    print("  py scripts/generate_demo_data.py")
    print("  py scripts/train.py --no-cv")
    print("  py scripts/smoke_test.py --spawn")
    print("  cd frontend && npm install && npm run build")


if __name__ == "__main__":
    main()
