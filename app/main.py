from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field



class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobCreateRequest(BaseModel):
    source_url: str | None = Field(
        default=None,
        description="Optional URL of the uploaded asset to process.",
    )
    metadata: dict[str, Any] = Field(
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
    metadata: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="Intria Jobs API",
    version="0.1.0",
)


_jobs: dict[str, JobReadResponse] = {}


@app.post("/v1/jobs", response_model=JobCreateResponse, status_code=201)
def create_job(payload: Optional[JobCreateRequest] = None) -> JobCreateResponse:
    payload = payload or JobCreateRequest()
    now = datetime.now(timezone.utc)
    job_id = str(uuid4())
    _jobs[job_id] = JobReadResponse(
        job_id=job_id,
        status=JobStatus.queued,
        created_at=now,
        updated_at=now,
        source_url=payload.source_url,
        metadata=payload.metadata,
    )
    return JobCreateResponse(job_id=job_id)


@app.get("/v1/jobs/{job_id}", response_model=JobReadResponse)
def get_job(job_id: str) -> JobReadResponse:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}