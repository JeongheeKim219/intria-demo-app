from dotenv import load_dotenv
from sqlalchemy import inspect, text

from app.database.db import Base, get_engine

load_dotenv()

import app.database.models  # noqa: F401

engine = get_engine()
Base.metadata.create_all(bind=engine)

inspector = inspect(engine)
job_columns = {column["name"] for column in inspector.get_columns("jobs")}

with engine.begin() as connection:
    # 기존 테이블이 있어도 이번 PR에 필요한 user_id 컬럼을 보장한다.
    if "user_id" not in job_columns:
        connection.execute(
            text("ALTER TABLE jobs ADD COLUMN user_id VARCHAR DEFAULT 'system' NOT NULL")
        )

    index_names = {index["name"] for index in inspector.get_indexes("jobs")}
    if "ix_jobs_user_id_job_id" not in index_names:
        connection.execute(
            text("CREATE INDEX ix_jobs_user_id_job_id ON jobs (user_id, job_id)")
        )

print("DB tables created")