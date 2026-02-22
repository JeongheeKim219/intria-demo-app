import logging
import json
import time
import uuid

import requests

from src.config import MissingConfigError, get_naver_ocr_config

logger = logging.getLogger(__name__)


# --- Naver Clova OCR 연동 함수 (수정) ---
def extract_text_with_clova_ocr(s3_url):
    logger.debug("Processing S3 URL: %s", s3_url)
    """
    S3에 업로드된 이미지 URL을 Naver Clova OCR API로 전송하여 텍스트를 추출합니다.
    """
    response = None
    try:
        # 1. Naver Clova OCR API 호출 준비
        ocr_config = get_naver_ocr_config()
        api_url = ocr_config["api_url"]
        secret_key = ocr_config["secret_key"]

        # 2. API 요청 본문(Body) 구성
        request_body = {
            "images": [
                {
                    "format": "png",  # 또는 jpeg
                    "name": "demo",
                    "url": s3_url,
                }
            ],
            "lang": "ko",
            "requestId": str(uuid.uuid4()),
            "version": "V2",
            "timestamp": int(round(time.time() * 1000)),
        }

        headers = {"X-OCR-SECRET": secret_key, "Content-Type": "application/json"}

        # 3. API 호출
        response = requests.post(
            api_url, headers=headers, data=json.dumps(request_body).encode("UTF-8")
        )
        response.raise_for_status()
        result = response.json()

        # 4. 결과에서 텍스트만 추출
        all_text = ""
        for field in result["images"][0]["fields"]:
            all_text += field["inferText"] + " "

        logger.info("✅ Naver Clova OCR 텍스트 추출 성공!")
        return all_text.strip()

    except MissingConfigError:
        raise
    except requests.exceptions.HTTPError as http_err:
        logger.error("Clova OCR API HTTP 오류 발생: %s", http_err)
        logger.error("응답 내용: %s", response.text if response is not None else "<no response>")
        return None
    except Exception as e:
        logger.exception("Clova OCR 처리 중 오류 발생: %s", e)
        return None
