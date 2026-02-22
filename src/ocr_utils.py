import logging
import streamlit as st
import requests
import json
import uuid
import time

logger = logging.getLogger(__name__)


# --- Naver Clova OCR 연동 함수 (수정) ---
def extract_text_with_clova_ocr(s3_url):
    logger.debug("Processing S3 URL: %s", s3_url)
    """
    S3에 저장된 이미지의 URL을 Naver Clova OCR API로 전송하여 텍스트를 추출합니다.
    """
    try:
        # 1. Naver Clova OCR API 호출 준비
        api_url = st.secrets["naver_ocr"]["api_url"]
        secret_key = st.secrets["naver_ocr"]["secret_key"]

        # 2. API 요청 본문(Body) 구성
        # 사용자가 알려준 정확한 형식으로, 이미지 데이터 대신 URL을 전달합니다.
        request_body = {
            'images': [
                {
                    'format': 'png', # 또는 jpeg
                    'name': 'demo',
                    'url': s3_url  # S3에 업로드된 파일의 public URL
                }
            ],
            'lang': 'ko',
            'requestId': str(uuid.uuid4()),
            'version': 'V2',
            'timestamp': int(round(time.time() * 1000))
        }

        headers = {
            'X-OCR-SECRET': secret_key,
            'Content-Type': 'application/json'
        }

        # 3. API 호출 (requests.post 사용)
        response = requests.post(api_url, headers=headers, data=json.dumps(request_body).encode('UTF-8'))
        response.raise_for_status() # 오류가 발생하면 예외를 발생시킵니다.
        result = response.json()

        # 4. 결과에서 텍스트만 추출하여 합치기
        all_text = ""
        for field in result['images'][0]['fields']:
            all_text += field['inferText'] + " "
        
        st.success("✅ Naver Clova OCR 텍스트 추출 성공!")
        return all_text.strip()

    except requests.exceptions.HTTPError as http_err:
        logger.error("Clova OCR API HTTP error: %s", http_err)
        st.error(f"Clova OCR API HTTP 오류 발생: {http_err}")
        st.error(f"응답 내용: {response.text}")
        logger.debug("Response content: %s", response.text)
        return None
    except Exception as e:
        logger.exception("Clova OCR processing error")
        st.error(f"Clova OCR 처리 중 오류 발생: {e}")
        return None

