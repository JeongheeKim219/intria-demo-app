import streamlit as st
from openai import OpenAI
import json
import ast  # 방어적 파싱을 위한 라이브러리



# Function tool schema: objective extraction with ranked items
objective_tool_schema = {
    "type": "function",
    "function": {
        "name": "extract_objective_analysis",
        "description": "Extract only objective data (Step 1) from OCR text of a mobile screenshot.",
        "parameters": {
            "type": "object",
            "properties": {
                "data_analysis_results": {
                    "type": "object",
                    "description": "Step 1: Objective information extracted by the Data Analyst.",
                    "properties": {
                        "content_type": { "type": "string", "description": "스크린샷 콘텐츠의 유형 (예: 소셜 미디어, 쇼핑, 영수증 등)" },
                        "main_topics": {
                            "type": "array", "description": "핵심 주제 후보. 각 항목에 중요도 '등급'을 부여해야 함.", "maxItems": 3,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {"type": "string", "description": "핵심 주제"},
                                    "importance": {"type": "integer", "description": "중요도 등급 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 여러 항목이 같은 등급을 가질 수 있음."}
                                }, "required": ["item", "importance"],
                            },
                        },
                        "entities": {
                            "type": "array", "description": "주요 개체명 후보. 각 항목에 중요도 '등급'을 부여해야 함.", "maxItems": 8,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {"type": "string", "description": "개체명"},
                                    "importance": {"type": "integer", "description": "중요도 등급 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 여러 항목이 같은 등급을 가질 수 있음."}
                                }, "required": ["item", "importance"],
                            },
                        },
                        "keywords": {
                            "type": "array", "description": "핵심 키워드 후보. 각 항목에 중요도 '등급'을 부여해야 함.", "maxItems": 8,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {"type": "string", "description": "키워드"},
                                    "importance": {"type": "integer", "description": "중요도 등급 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 여러 항목이 같은 등급을 가질 수 있음."}
                                }, "required": ["item", "importance"],
                            },
                        },
                    }, "required": ["content_type", "main_topics", "entities", "keywords"],
                }
            }, "required": ["data_analysis_results"],
        },
    },
}


def _coerce_int(value, default=999):
    try:
        return int(value)
    except Exception:
        return default


def _normalize_ranked_list(value, top_n, importance_threshold=5): # 기본 임계값을 5로 넉넉하게 설정
    """Normalize a ranked list into top-N unique strings.
    Accepts list of objects {item, importance} or list of strings.
    Deterministically sorts, deduplicates, and slices to top_n.
    """
    if not isinstance(value, list): return []

    rows = []
    for idx, elem in enumerate(value):
        item, imp = None, 999
        parsed_dict = None
        if isinstance(elem, dict):
            parsed_dict = elem
        elif isinstance(elem, str):
            try:
                parsed_dict = ast.literal_eval(elem)
                if not isinstance(parsed_dict, dict): parsed_dict = None
            except (ValueError, SyntaxError):
                parsed_dict = None

        if parsed_dict:
            item = parsed_dict.get("item")
            imp = _coerce_int(parsed_dict.get("importance", 999), 999)
        else:
            item = str(elem) if elem is not None else None

        if imp > importance_threshold: continue
        if not item or not item.strip(): continue

        rows.append((imp, idx, item.strip()))

    rows.sort(key=lambda t: (t[0], t[1]))

    seen, out = set(), []
    for _, __, item in rows:
        key = item.lower()
        if key in seen: continue
        seen.add(key)
        out.append(item)
        if len(out) >= top_n: break
    return out

def analyze_text_objective(text):
    # Basic error handling
    if not text or not text.strip():
        return {"error": "분석할 텍스트가 없습니다."}

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a meticulous Data Analyst for mobile OCR text. "
                    "Your task is to extract objective information using the 'extract_objective_analysis' tool. "
                    "You MUST assign an **importance level (1=very high, 5=very low)** to each item. "
                    "**Multiple items can share the same importance level.**"
                    "The output language must match the input text's language."
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
            temperature=0,
        )

        result_json = response.choices[0].message.tool_calls[0].function.arguments
        st.success("객관 정보 분석 완료")
        parsed = json.loads(result_json)
        dar = parsed.get("data_analysis_results", parsed)

        if isinstance(dar, dict):
            # Preserve raw lists (before importance-based normalization) for UI comparison
            raw_main = dar.get("main_topics", [])
            raw_entities = dar.get("entities", [])
            raw_keywords = dar.get("keywords", [])
            dar["main_topics_raw"] = raw_main
            dar["entities_raw"] = raw_entities
            dar["keywords_raw"] = raw_keywords

            # Normalize to top-N unique strings (after importance selection)
            # [임계점 적용 수정] 함수 호출 시, 각 항목에 맞는 '중요도 임계값'을 지정
            # 주제는 1~2순위만, 개체/키워드는 1~3순위만 최종 데이터로 인정
            dar["main_topics"] = _normalize_ranked_list(raw_main, top_n=3, importance_threshold=2)
            dar["entities"] = _normalize_ranked_list(raw_entities, top_n=5, importance_threshold=3)
            dar["keywords"] = _normalize_ranked_list(raw_keywords, top_n=5, importance_threshold=3)

        return dar

    except Exception as e:
        st.error(f"객관 정보 분석 오류: {e}")


# Function tool schema: aggregate creative profile (kept as strings)
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
    },
}


def aggregate_user_profile(objective_data_points):
    if not objective_data_points:
        return None

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Creative Profiler. Given multiple objective analyses, aggregate them to infer a user interest profile. "
                    "Use only the provided objective data and consider the cultural context relevant to the language of the input data. "
                    "**Crucially, the output language of all string values MUST match the predominant language of the input data points.**"
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
            temperature=0,
        )

        result_json = response.choices[0].message.tool_calls[0].function.arguments
        st.success("집계 프로필 생성 완료")
        parsed = json.loads(result_json)
        return parsed.get("creative_profiling_results", parsed)

    except Exception as e:
        st.error(f"프로필 생성 오류: {e}")
        return None
    

def _to_string_list(raw_list):
    """Coerce a possibly mixed list (dicts with {item, importance} or strings)
    into a simple list[str], preserving order and skipping empty values.
    """
    if not isinstance(raw_list, list):
        return []
    out = []
    for elem in raw_list:
        if isinstance(elem, dict):
            val = elem.get("item")
        else:
            val = elem
        if val is None:
            continue
        s = str(val).strip()
        if not s:
            continue
        out.append(s)
    return out


def aggregate_user_profile_before_after(objective_data_points):
    """
    (수정) Before/After 데이터를 각각 준비하고, 수정된 aggregate_user_profile 함수를
    두 번 호출하여 결과를 반환합니다.
    """
    if not objective_data_points:
        return None, None

    before_points = []
    after_points = []
    for dp in objective_data_points:
        if not isinstance(dp, dict):
            continue
        content_type = dp.get("content_type")

        # Before 데이터 준비 (raw 데이터 사용)
        mt_raw = dp.get("main_topics_raw", dp.get("main_topics", []))
        ent_raw = dp.get("entities_raw", dp.get("entities", []))
        kw_raw = dp.get("keywords_raw", dp.get("keywords", []))

        before_points.append({
            "content_type": content_type,
            "main_topics": _to_string_list(mt_raw),
            "entities": _to_string_list(ent_raw),
            "keywords": _to_string_list(kw_raw),
        })

        # After 데이터 준비 (정제된 데이터 사용)
        after_points.append({
            "content_type": content_type,
            "main_topics": dp.get("main_topics", []),
            "entities": dp.get("entities", []),
            "keywords": dp.get("keywords", []),
        })

    # 이제 제대로 작동하는 aggregate_user_profile 함수를 각각 호출합니다.
    st.info("정제 전(Before) 데이터로 프로파일링을 시작합니다...")
    before_profile = aggregate_user_profile(before_points)
    
    st.info("정제 후(After) 데이터로 프로파일링을 시작합니다...")
    after_profile = aggregate_user_profile(after_points)
    
    return before_profile, after_profile