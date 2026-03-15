import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_user_id_job_id", "user_id", "job_id"),
    )

    job_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    status = Column(String, nullable=False)          # queued/running/succeeded/failed
    progress = Column(Integer, nullable=False, default=0)
    current_step = Column(String, nullable=True)     # start/ocr/analysis/indexing
    attempt = Column(Integer, nullable=False, default=0)

    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    source_url = Column(Text, nullable=True)
    item_id = Column(String, nullable=True)

    metadata_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    def metadata_dict(self):
        # API 응답에서는 JSON 문자열을 dict로 복원해서 반환한다.
        return json.loads(self.metadata_json or "{}")


class Item(Base):
    __tablename__ = "items"

    item_id = Column(String, primary_key=True)
    source_url = Column(Text, nullable=False)
    image_hash = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class OCRResult(Base):
    __tablename__ = "ocr_results"

    item_id = Column(String, ForeignKey("items.item_id"), primary_key=True)
    text = Column(Text, nullable=False)
    raw_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    item_id = Column(String, ForeignKey("items.item_id"), primary_key=True)
    objective_json = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class EmbeddingRef(Base):
    __tablename__ = "embeddings"

    item_id = Column(String, ForeignKey("items.item_id"), primary_key=True)
    vector_ref = Column(Text, nullable=False)  # ex: "faiss:doc_id=<item_id>"
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
