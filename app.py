import streamlit as st
from PIL import Image
from src.aws_utils import upload_file_to_s3
from src.ocr_utils import extract_text_with_clova_ocr
from src.ai_utils import analyze_text_objective, aggregate_user_profile

if "history" not in st.session_state:
    st.session_state["history"] = []


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


if uploaded_files:
    st.subheader("🔍 분석 실행")
    if st.button(f"{len(uploaded_files)}개 파일 분석 시작하기"):
        batch_objectives = []
        # 전역 진행 상황 표시 (많은 이미지 처리 시 유용)
        total_images = len(uploaded_files)
        processed_count = 0
        success_count = 0
        progress_container = st.container()
        status_text = progress_container.empty()
        progress_bar = progress_container.progress(0)

        for uploaded_file in uploaded_files:
            with st.expander(f"'{uploaded_file.name}' 분석 결과", expanded=False):
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(uploaded_file, caption="업로드된 이미지", use_container_width=True)
                
                with col2:
                    s3_file_url = None
                    extracted_text = None
                    objective_result = None

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
                        st.text_area("OCR Text", extracted_text, height=200, key=f"text_for_{uploaded_file.name}")
                        with st.spinner("이미지별 분석을 수행 중..."):
                            objective_result = analyze_text_objective(extracted_text)
                            
                    # 이미지별 데이터 분석 결과 출력
                    if objective_result:
                        st.success("✅ 이미지별 객관 분석 성공!")
                        st.json(objective_result)  # Step 1 결과만 표시
                        batch_objectives.append(objective_result)
                        success_count += 1
                    elif extracted_text: # 데이터 분석 실패했지만 OCR은 성공한 경우
                        st.error("이미지별 데이터 분석에 실패했습니다.")
                    elif s3_file_url: # OCR부터 실패한 경우
                        st.error("텍스트 추출에 실패했습니다.")

                    # 전역 진행률 업데이트 (이 이미지 처리 완료)
                    processed_count += 1
                    percent = int(processed_count / total_images * 100)
                    progress_bar.progress(percent)
                    status_text.text(
                        f"GPT 분석 완료: {success_count}/{total_images} · 처리됨: {processed_count}/{total_images}"
                    )

                    st.session_state["history"].append(
                        {
                            "filename": uploaded_file.name,
                            "s3_url": s3_file_url,
                            "extracted_text": extracted_text,
                            "objective_result": objective_result,
                        }
                    )

        # 배치 단위 통합 사용자 프로필
        if batch_objectives:
            st.markdown("---")
            st.subheader("👤 통합 사용자 프로필 (이번 세션 기준)")
            with st.spinner("여러 이미지 결과를 통합하여 프로필 생성 중..."):
                aggregated_profile = aggregate_user_profile(batch_objectives)
            if aggregated_profile:
                st.success("✅ 통합 프로필 생성 완료")
                st.json(aggregated_profile)
            else:
                st.error("통합 프로필 생성에 실패했습니다.")

