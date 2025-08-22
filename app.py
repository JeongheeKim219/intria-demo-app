import streamlit as st
from PIL import Image
from src.aws_utils import upload_file_to_s3
# from src.processing import analyze_image_with_ai
# from src.ui_components import display_analysis_results

# --- 1. 페이지 기본 설정 ---
st.set_page_config(
    page_title="AI 스크린샷 정보 추출기",
    page_icon="🧐",
    layout="wide"
)

# --- 2. 사이드바 UI ---
with st.sidebar:
    st.header("📜 사용 안내")
    st.info(
        "이 앱은 스크린샷에서 유용한 정보를 추출하고 요약합니다. "
        "분석하고 싶은 이미지를 업로드하고 '분석 시작' 버튼을 눌러주세요."
    )
    st.warning(
        "이 프로젝트는 AI 대학원 포트폴리오 제출을 위해 제작되었습니다. "
        "실제 서비스가 아니므로 데모용으로만 사용해주세요."
    )

# --- 3. 메인 화면 UI ---
st.title("AI 스크린샷 정보 추출기")
st.markdown("---")

# 파일 업로더 위젯
uploaded_file = st.file_uploader(
    "분석할 스크린샷 이미지를 업로드하세요.",
    type=['png', 'jpg', 'jpeg']
)

# 파일이 업로드되었을 때만 아래 로직 실행
if uploaded_file is not None:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🖼️ 원본 이미지")
        st.image(uploaded_file, caption="업로드된 이미지", use_container_width=True)

    with col2:
        st.subheader("🔍 분석 실행")
        if st.button("S3에 업로드하고 분석 시작하기"):
            s3_file_url = None # S3 URL 초기화
            analysis_result = None # 분석 결과 초기화

            # 1단계: S3에 파일 업로드
            with st.spinner("파일을 S3에 업로드하는 중..."):
                # 실제 로직은 src/aws_utils.py에 있는 함수를 호출합니다.
                s3_file_url = upload_file_to_s3(uploaded_file)

            # # 2단계: S3 업로드 성공 시 AI 분석 실행
            # if s3_file_url:
            #     st.info(f"S3 업로드 완료: {s3_file_url}")
            #     with st.spinner("AI가 이미지를 분석하고 있습니다... (OCR, LLM)"):
            #         # 실제 AI 처리 로직은 src/processing.py에 있는 함수를 호출합니다.
            #         # 이 함수는 S3 URL을 받아 Lambda를 트리거하거나 직접 처리할 수 있습니다.
            #         analysis_result = analyze_image_with_ai(s3_file_url)

            # # 3단계: 분석 결과 출력
            # if analysis_result:
            #     st.success("✅ 분석이 완료되었습니다!")
            #     # 실제 결과 출력 UI는 src/ui_components.py에 있는 함수를 호출합니다.
            #     display_analysis_results(analysis_result)
            # else:
            #     st.error("분석 과정에서 오류가 발생했습니다.")
else:
    st.warning("이미지를 업로드하여 분석을 시작하세요.")

