import streamlit as st
from PIL import Image
from src.aws_utils import upload_file_to_s3
from src.ocr_utils import extract_text_with_clova_ocr
from src.ai_utils import analyze_text_with_gpt


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
uploaded_files = st.file_uploader(
    "분석할 스크린샷 이미지를 업로드하세요.",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)


# uploaded_files는 이제 단일 파일이 아닌 파일 리스트입니다.
if uploaded_files:
    st.subheader("🔍 분석 실행")
    if st.button(f"{len(uploaded_files)}개 파일 분석 시작하기"):
        # 각 파일에 대한 처리 과정을 깔끔하게 보여주기 위해 st.expander를 사용합니다.
        for uploaded_file in uploaded_files:
            with st.expander(f"'{uploaded_file.name}' 분석 결과", expanded=True):
                
                # UI를 두 개의 컬럼으로 나누어 이미지와 결과를 나란히 표시합니다.
                col1, col2 = st.columns(2)
                with col1:
                    st.image(uploaded_file, caption="업로드된 이미지", use_container_width=True)
                
                with col2:
                    s3_file_url = None
                    extracted_text = None
                    analysis_result = None

                    with st.spinner("파일을 S3에 업로드하는 중..."):
                        s3_file_url = upload_file_to_s3(uploaded_file)

                    # S3 업로드 성공 시 OCR 분석 실행
                    if s3_file_url:
                        st.info(f"S3 업로드 완료. OCR 분석을 시작합니다.")
                        with st.spinner("이미지에서 텍스트를 읽고 있습니다..."):
                            st.write(s3_file_url)
                            extracted_text = extract_text_with_clova_ocr(s3_file_url)

                    # OCR 결과 출력
                    if extracted_text:
                        st.subheader("📄 OCR 추출 결과")
                        # 각 text_area는 고유한 key를 가져야 하므로 파일 이름을 사용합니다.
                        st.text_area("OCR Text", extracted_text, height=200, key=f"text_for_{uploaded_file.name}")
                        with st.spinner("GPT가 텍스트를 분석하고 있습니다..."):
                            analysis_result = analyze_text_with_gpt(extracted_text)
                            
                    # GPT 분석 결과 출력
                    if analysis_result:
                        st.success("✅ GPT 구조화 분석 성공!")
                        st.json(analysis_result) # JSON 결과를 예쁘게 보여줍니다.
                    elif extracted_text: # GPT는 실패했지만 OCR은 성공한 경우
                        st.error("GPT 분석에 실패했습니다.")
                    elif s3_file_url: # OCR부터 실패한 경우
                        st.error("텍스트 추출에 실패했습니다.")
