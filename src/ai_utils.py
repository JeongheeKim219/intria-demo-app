import streamlit as st
from openai import OpenAI
import json


# 이미지에서 객관적 데이터만 추출하는 함수 스키마
objective_tool_schema = {
    "type": "function",
    "function": {
        "name": "extract_objective_analysis",
        "description": "Extracts only objective data (Step 1) from OCR text of a mobile screenshot.",
        "parameters": {
            "type": "object",
            "properties": {
                "data_analysis_results": {
                    "type": "object",
                    "description": "Step 1: Objective information extracted by the Data Analyst.",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "스크린샷 콘텐츠의 유형을 분류합니다. (예: 소셜 미디어, 메신저, 쇼핑, 웹 검색 결과)",
                            "enum": ["소셜 미디어", "메신저", "쇼핑", "웹 검색 결과", "영수증", "예매내역", "시간표", "기타"]
                        },
                        "main_topics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "스크린샷의 전체 내용을 한 단어 또는 구로 요약하는 가장 핵심적인 주제 최대 3개"
                        },
                        "entities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "언급된 주요 고유 명사(장소, 브랜드, 인물, 제품명 등). 중요도 순 최대 5개"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "콘텐츠 이해를 돕는 핵심 키워드(고유 명사 제외). 관련성 높은 순 최대 5개"
                        }
                    },
                    "required": ["content_type", "main_topics", "entities", "keywords"]
                }
            },
            "required": ["data_analysis_results"]
        }
    }
}


def analyze_text_objective(text):
    # error 처리
    if not text or not text.strip():
        return {"error": "분석할 텍스트가 없습니다."}

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a meticulous Data Analyst for Korean mobile OCR text. "
                    "Extract only objective information (Step 1) and return results by calling the provided tool. "
                    "Do not infer interests or add creative profiling."
                ),
            },
            {
                "role": "user",
                "content": f"""Extract only Step 1 objective analysis from the following OCR text and return using 'extract_objective_analysis'.
                --- OCR TEXT START---
                {text}
                --- OCR TEXT END ---""",
            },
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=[objective_tool_schema],
            tool_choice={"type": "function", "function": {"name": "extract_objective_analysis"}},
        )

        result_json = response.choices[0].message.tool_calls[0].function.arguments
        st.success("이미지별 데이터 분석 완료")
        # 내부 data_analysis_results만 꺼내서 단순하게 반환함
        parsed = json.loads(result_json)
        return parsed.get("data_analysis_results", parsed)

    except Exception as e:
        st.error(f"이미지별 데이터 분석 중 오류 발생: {e}")
        return None


# 세션 단위로 유저 분리 - 유저에 대한 해석, 프로파일 생성
aggregate_tool_schema = {
    "type": "function",
    "function": {
        "name": "generate_aggregated_profile",
        "description": "Generates a single creative profiling result by aggregating multiple objective analyses.",
        "parameters": {
            "type": "object",
            "properties": {
                "creative_profiling_results": {
                    "type": "object",
                    "properties": {
                        "inferred_user_interests": {"type": "array", "items": {"type": "string"}},
                        "new_tag_suggestions": {"type": "array", "items": {"type": "string"}},
                        "profiler_summary": {"type": "string"},
                    },
                    "required": ["inferred_user_interests", "new_tag_suggestions", "profiler_summary"],
                }
            },
            "required": ["creative_profiling_results"],
        },
    }
}


def aggregate_user_profile(objective_data_points):
    """
    objective_data_points: 여러 이미지에서 나온 Step 1 결과
    각 dict는 content_type, main_topics, entities, keywords 키를 가짐
    """
    if not objective_data_points:
        return None

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Creative Profiler. Given multiple objective analyses from Korean mobile OCR, "
                    "aggregate them to infer a single, robust user interest profile. "
                    "Use only the provided objective data (content_type, main_topics, entities, keywords). "
                    "Return the result by calling the provided tool."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Aggregate the following objective analyses into one creative profile. "
                    "Prefer recurring topics/entities and avoid overfitting to one-off noise.\n\n"
                    + json.dumps({"objective_data_points": objective_data_points}, ensure_ascii=False)
                ),
            },
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            tools=[aggregate_tool_schema],
            tool_choice={"type": "function", "function": {"name": "generate_aggregated_profile"}},
        )

        result_json = response.choices[0].message.tool_calls[0].function.arguments
        st.success("통합 사용자 프로필 생성 성공")
        parsed = json.loads(result_json)
        return parsed.get("creative_profiling_results", parsed)

    except Exception as e:
        st.error(f"통합 프로필 생성 중 오류 발생: {e}")
        return None
