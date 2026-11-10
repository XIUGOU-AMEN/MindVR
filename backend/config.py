"""集中式配置。所有密钥只从环境变量读取，仓库内不保存任何凭据。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    llm_backend: str = "local"

    local_base_url: str = "http://127.0.0.1:8001/v1"
    local_model: str = "qwen2.5-7b-instruct"
    local_api_key: str = "EMPTY"

    maas_base_url: str = ""
    maas_model: str = ""
    maas_api_key: str = ""

    huawei_ak: str = ""
    huawei_sk: str = ""
    huawei_project_id: str = ""
    huawei_region: str = "cn-north-4"
    obs_bucket: str = ""
    use_cloud_storage: bool = False
    use_cloud_asr: bool = False
    sis_asr_max_seconds: float = 55.0
    sis_asr_property: str = "chinese_16k_general"

    database_url: str = "sqlite:///./data/app.db"
    redis_url: str = ""

    model_path: str = "models/phq8_model.joblib"
    phq8_binary_threshold: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def model_file(self) -> Path:
        path = Path(self.model_path)
        return path if path.is_absolute() else ROOT_DIR / path

    @property
    def demo_dir(self) -> Path:
        return ROOT_DIR / "data" / "demo"

    @property
    def sqlalchemy_url(self) -> str:
        if not self.database_url.startswith("sqlite"):
            return self.database_url
        prefix = "sqlite:///"
        raw = self.database_url[len(prefix) :]
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT_DIR / raw
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
