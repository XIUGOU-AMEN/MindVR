"""数据库层。本地默认 SQLite，线上通过 DATABASE_URL 切换到华为云 RDS MySQL。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import get_settings

settings = get_settings()
engine = create_engine(settings.sqlalchemy_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    participant_id: Mapped[str] = mapped_column(String(64), index=True)
    phq8_score: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float)
    classification: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(16))
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def init_db() -> None:
    Base.metadata.create_all(engine)
