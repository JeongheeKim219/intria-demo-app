"""Streamlit page for displaying analysis history."""

import streamlit as st


st.title("📚 Analysis History")

history = st.session_state.get("history", [])

if not history:
    st.info("아직 분석 기록이 없습니다. 메인 페이지에서 이미지를 분석해 주세요.")
else:
    for i, record in enumerate(history):
        with st.expander(record["filename"], expanded=False):
            if record.get("analysis_result"):
                st.subheader("GPT 분석 결과")
                st.json(record["analysis_result"])
            if record.get("extracted_text"):
                st.subheader("OCR 텍스트")
                st.text_area(
                    "텍스트",
                    record["extracted_text"],
                    height=200,
                    key=f"history_{record['filename']}_{i}",
                )
