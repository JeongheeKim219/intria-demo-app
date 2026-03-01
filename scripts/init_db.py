from dotenv import load_dotenv
load_dotenv()

from app.database.db import engine, Base
import app.database.models  # noqa: F401  모델 로드가 필요

Base.metadata.create_all(bind=engine)
print("DB tables created")