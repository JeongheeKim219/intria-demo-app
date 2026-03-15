from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field



## 유저별 서비스 제공을 위한 기초 셋팅 1
#유저 식별(데모용)은 헤더의 X-User-Id로 처리, 유저 식별 없이는 401 에러 반환
def get_current_user(x_user_id: str | None = Header(None, alias="X-User-Id")) -> str:
    if x_user_id is None or x_user_id.strip() == "":
        raise HTTPException(status_code=401, detail="Unauthorized: Missing X-User-Id header")
    return x_user_id.strip()



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



## 유저별 서비스 제공을 위한 기초 셋팅 2
# 유저별로 Job을 분리저장(PostgreSQL 적용 전 임시 in-memory 저장소)
_jobs_by_user: dict[str, dict[str, JobReadResponse]] = {}


@app.post("/v1/jobs", response_model=JobCreateResponse, status_code=201)
def create_job(
    payload: Optional[JobCreateRequest] = None,
    user_id: str = Depends(get_current_user),
) -> JobCreateResponse:
    payload = payload or JobCreateRequest()
    now = datetime.now(timezone.utc)
    job_id = str(uuid4())

    # 유저 스코프 저장소가 없으면 만든다.
    _jobs_by_user.setdefault(user_id, {})
    _jobs_by_user[user_id][job_id] = JobReadResponse(
        job_id=job_id,
        status=JobStatus.queued,
        created_at=now,
        updated_at=now,
        source_url=payload.source_url,
        metadata=payload.metadata,
    )
    return JobCreateResponse(job_id=job_id)



## 유저별 서비스 제공을 위한 기초 셋팅 3
@app.get("/v1/jobs/{job_id}", response_model=JobReadResponse)
def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
) -> JobReadResponse:
    # 같은 job_id라도 유저가 다르면 접근 불가(404)
    job = _jobs_by_user.get(user_id, {}).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}