import os
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

SessionLocal = sessionmaker(autocommit=False, autoflush=False)
_engine = None  # type: Optional[Engine]

Base = declarative_base()


def get_database_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


def get_engine() -> Engine:
    global _engine

    if _engine is None:
        database_url = get_database_url()
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Create a .env file (see .env.example) or set DATABASE_URL in your environment."
            )
        _engine = create_engine(database_url, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    # 환경변수가 늦게 주입돼도 요청 시점에 세션을 열 수 있게 지연 초기화
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
