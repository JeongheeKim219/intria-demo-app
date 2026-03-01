# models.py
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from app.database.db import Base

def utcnow():
    return datetime.now(timezone.utc)

class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)          # queued/running/succeeded/failed
    progress = Column(Integer, nullable=False, default=0)
    current_step = Column(String, nullable=True)     # start/ocr/analysis/indexing
    attempt = Column(Integer, nullable=False, default=0)

    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    source_url = Column(Text, nullable=True)
    item_id = Column(String, nullable=True)          # succeeded 시 연결

    metadata_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

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