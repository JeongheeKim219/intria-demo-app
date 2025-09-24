import streamlit as st
from PIL import Image
from src.aws_utils import upload_file_to_s3
from src.ocr_utils import extract_text_with_clova_ocr
from src.ai_utils import analyze_text_objective, aggregate_user_profile_before_after

if "history" not in st.session_state:
    st.session_state["history"] = []


# --- 1. 페이지 기본 설정 ---
st.set_page_config(
    page_title="AI 스크린샷 정보 추출",
    page_icon="🧐",
    layout="wide",
)

# --- 2. 사이드바 UI ---
with st.sidebar:
    st.header("사용 안내")
    st.info(
        "여러 장의 스크린샷에서 정보를 추출하고 요약합니다. "
        "분석 단계와 최종 집계 프로필을 생성합니다."
    )
    st.warning("실제 서비스가 아니므로 데모용으로만 사용해주시기 바랍니다.")

# --- 3. 메인 화면 UI ---
st.title("AI 스크린샷 정보 추출")
st.markdown("---")

# 파일 업로더 위젯
uploaded_files = st.file_uploader(
    "분석할 스크린샷 이미지를 업로드하세요.",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.subheader("배치 분석 진행")
    if st.button(f"{len(uploaded_files)}개 파일 분석 시작하기"):
        batch_objectives = []
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

                    with st.spinner("파일을 S3에 업로드 중..."):
                        s3_file_url = upload_file_to_s3(uploaded_file)

                    # S3 업로드 성공 후 OCR 분석 수행
                    if s3_file_url:
                        st.info("S3 업로드 완료. OCR 분석을 시작합니다.")
                        with st.spinner("이미지에서 텍스트 추출 중..."):
                            st.write(s3_file_url)
                            extracted_text = extract_text_with_clova_ocr(s3_file_url)

                    # 업로드/추출 결과에 따른 처리
                    if not s3_file_url:
                        st.error("S3 업로드 실패로 분석을 진행하지 못했습니다.")
                    elif extracted_text and str(extracted_text).strip():
                        st.subheader("OCR 추출 결과")
                        st.text_area(
                            "OCR Text",
                            extracted_text,
                            height=200,
                            key=f"text_for_{uploaded_file.name}",
                        )
                        with st.spinner("객관적 데이터 분석 진행 중..."):
                            objective_result = analyze_text_objective(extracted_text)
                    else:
                        # 텍스트 추출 실패 시: 이미지 전용으로 분류
                        st.info("텍스트를 추출하지 못해 이미지 전용으로 분류합니다.")
                        objective_result = {
                            "content_type": "image_only",
                            "main_topics": [],
                            "entities": [],
                            "keywords": [],
                        }
                        st.json(objective_result)

                    # 결과 출력 및 배치 집계 포함 여부 결정
                    if objective_result:
                        if isinstance(objective_result, dict) and objective_result.get("content_type") == "image_only":
                            # 이미지 전용은 배치 집계 제외
                            pass
                        else:
                            st.success("🎉 객관적 데이터 분석 성공!")
                            st.json(objective_result)

                            # 중요도 적용 전/후 비교
                            if all(k in objective_result for k in [
                                "main_topics_raw", "entities_raw", "keywords_raw"
                            ]):
                                with st.expander("중요도 적용 전/후 비교", expanded=False):
                                    tabs = st.tabs(["주제", "개체", "키워드"])

                                    with tabs[0]:
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.caption("적용 전 (Raw)")
                                            st.json(objective_result.get("main_topics_raw", []))
                                        with col_b:
                                            st.caption("적용 후 (Top-N)")
                                            st.json(objective_result.get("main_topics", []))

                                    with tabs[1]:
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.caption("적용 전 (Raw)")
                                            st.json(objective_result.get("entities_raw", []))
                                        with col_b:
                                            st.caption("적용 후 (Top-N)")
                                            st.json(objective_result.get("entities", []))

                                    with tabs[2]:
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.caption("적용 전 (Raw)")
                                            st.json(objective_result.get("keywords_raw", []))
                                        with col_b:
                                            st.caption("적용 후 (Top-N)")
                                            st.json(objective_result.get("keywords", []))

                            batch_objectives.append(objective_result)
                            success_count += 1
                    elif extracted_text:
                        st.error("이미지의 객관적 데이터 분석이 실패하였습니다.")

                    # 진행 상태 업데이트
                    processed_count += 1
                    percent = int(processed_count / total_images * 100)
                    progress_bar.progress(percent)
                    status_text.text(
                        f"GPT 분석 완료: {success_count}/{total_images} · 처리: {processed_count}/{total_images}"
                    )

                    # 히스토리 기록
                    st.session_state["history"].append(
                        {
                            "filename": uploaded_file.name,
                            "s3_url": s3_file_url,
                            "extracted_text": extracted_text,
                            "objective_result": objective_result,
                        }
                    )

        # 배치 단위 집계 프로필 생성
        if batch_objectives:
            st.markdown("---")
            st.subheader("이번 배치 집계 프로필 (세션 기준)")
            with st.spinner("여러 이미지 결과를 합쳐 프로파일 생성 중..."):
                before_profile, after_profile = aggregate_user_profile_before_after(batch_objectives)
            if before_profile or after_profile:
                st.success("✅ 집계 프로필 생성 완료")
                with st.expander("프로파일링 중요도 적용 전/후 비교", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("적용 전 (Raw 기반)")
                        st.json(before_profile or {})
                    with col2:
                        st.subheader("적용 후 (Top-N 기반)")
                        st.json(after_profile or {})
            else:
                st.error("집계 프로필 생성에 실패했습니다.")
