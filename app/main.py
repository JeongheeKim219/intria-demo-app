import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import Job

load_dotenv()


# 유저 식별은 헤더의 X-User-Id로 고정하고, 값이 없으면 401을 반환한다.
def get_current_user(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> str:
    if x_user_id is None or x_user_id.strip() == "":
        raise HTTPException(status_code=401, detail="Unauthorized: Missing X-User-Id header")
    return x_user_id.strip()


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobCreateRequest(BaseModel):
    source_url: Optional[str] = Field(
        default=None,
        description="Optional URL of the uploaded asset to process.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata attached by the client.",
    )


class JobCreateResponse(BaseModel):
    job_id: str


class JobReadResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="Intria Jobs API",
    version="0.1.0",
)


@app.post("/v1/jobs", response_model=JobCreateResponse, status_code=201)
def create_job(
    payload: Optional[JobCreateRequest] = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    payload = payload or JobCreateRequest()
    now = datetime.now(timezone.utc)
    job_id = str(uuid4())

    # 이번 PR에서는 queued 상태만 저장하고, user_id 스코프를 함께 고정한다.
    job = Job(
        job_id=job_id,
        user_id=user_id,
        status=JobStatus.queued.value,
        progress=0,
        current_step=None,
        attempt=0,
        created_at=now,
        updated_at=now,
        source_url=payload.source_url,
        metadata_json=json.dumps(payload.metadata),
    )
    db.add(job)
    db.commit()

    return JobCreateResponse(job_id=job_id)


@app.get("/v1/jobs/{job_id}", response_model=JobReadResponse)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobReadResponse:
    # 같은 job_id라도 user_id가 다르면 404가 되도록 조회 조건을 강제한다.
    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobReadResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        source_url=job.source_url,
        metadata=job.metadata_dict(),
    )


@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}
