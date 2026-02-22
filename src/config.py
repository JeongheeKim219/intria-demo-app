import os
from typing import Any


class MissingConfigError(RuntimeError):
    """Raised when a required environment variable is missing."""


def _require_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    joined = ", ".join(names)
    raise MissingConfigError(f"Missing required environment variable. Set one of: {joined}")



def get_openai_api_key() -> str:
    return _require_env("OPENAI_API_KEY")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def get_aws_config() -> dict[str, Any]:
    return {
        "aws_access_key_id": _require_env("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": _require_env("AWS_SECRET_ACCESS_KEY"),
        "aws_region_name": _require_env("AWS_REGION"),
        "aws_storage_bucket_name": _require_env("S3_BUCKET_NAME"),
        "aws_querystring_auth": _env_bool("AWS_QUERYSTRING_AUTH", default=False),
    }


def get_naver_ocr_config() -> dict[str, str]:
    return {
        "api_url": _require_env("NAVER_OCR_API_URL"),
        "secret_key": _require_env("NAVER_OCR_SECRET_KEY"),
    }
