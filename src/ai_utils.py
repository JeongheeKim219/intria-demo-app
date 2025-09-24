import streamlit as st
from openai import OpenAI
import json
import ast  # 방어적 파싱을 위한 라이브러리



# Function tool schema:  중요도 반영, 중요도는 순위가 아니라 등급으로 반영.
objective_tool_schema = {
    "type": "function",
    "function": {
        "name": "extract_objective_analysis",
        "description": "모바일 스크린샷의 OCR 텍스트에서 객관적인 정보를 추출합니다. 추출결과는 반드시 입력 텍스트와 동일한 언어로 작성되어야 한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "data_analysis_results": {
                    "type": "object",
                            "description": "핵심 키워드 목록 (고유명사 제외). 반드시 입력 텍스트와 동일한 언어로 작성되어야 한다.",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "스크린샷의 콘텐츠 유형 (예: 소셜 미디어, 쇼핑, 영수증, 티켓, 시간표 등)."
                        },
                        "main_topics": {
                            "type": "array",
                            "description": "핵심 주제 목록. 각 주제는 반드시 중요도 등급을 포함해야 합니다.",
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {
                                        "type": "string",
                                        "description": "핵심 주제 (입력 텍스트와 동일한 언어로 작성)."
                                    },
                                    "importance": {
                                        "type": "integer",
                                        "description": "중요도 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 동일 등급 부여 및 특정 등급 건너뛰기 가능."
                                    }
                                },
                                "required": ["item", "importance"]
                            }
                        },
                        "entities": {
                            "type": "array",
                            "description": "주요 개체명 목록 (장소, 브랜드, 인물 등). 각 개체는 반드시 중요도 등급을 포함해야 합니다. 반드시 입력 텍스트와 동일한 언어로 작성되어야 한다.",
                            "maxItems": 5,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {
                                        "type": "string",
                                        "description": "개체명. 반드시 입력 텍스트와 동일한 언어로 작성."
                                    },
                                    "importance": {
                                        "type": "integer",
                                        "description": "중요도 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 동일 등급 부여 및 특정 등급 건너뛰기 가능."
                                    }
                                },
                                "required": ["item", "importance"]
                            }
                        },
                        "keywords": {
                            "type": "array",
                            "description": "핵심 키워드 목록 (고유명사 제외). 키워드는 입력 텍스트와 동일한 언어로 작성되어야 하며 각 키워드는 반드시 중요도 등급을 포함해야 합니다.",
                            "maxItems": 5,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {
                                        "type": "string",
                                        "description": "키워드. 반드시 입력 텍스트와 동일한 언어로 작성."
                                    },
                                    "importance": {
                                        "type": "integer",
                                        "description": "중요도 (1=매우 중요, 5=관련성 낮음). 순위가 아니므로 동일 등급 부여 및 특정 등급 건너뛰기 가능."
                                    }
                                },
                                "required": ["item", "importance"]
                            }
                        }
                    },
                    "required": ["content_type", "main_topics", "entities", "keywords"]
                }
            },
            "required": ["data_analysis_results"]
        }
    }
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
                    "당신은 모바일 OCR 텍스트를 분석하는 유능한 데이터 분석가입니다. "
                    "주어진 함수(tool)를 사용하여 객관적인 정보를 추출해야 합니다. "
                    "각 항목에는 반드시 **중요도 등급(1=매우 중요, 5=관련성 낮음)**을 부여해야 하며, "
                    "**여러 항목이 동일한 등급을 가질 수 있습니다.** "
                    "모든 출력값은 반드시 입력된 OCR 텍스트의 언어와 일치해야 합니다."
                ),
            },
            {
                "role": "user",
                "content": f"""다음 OCR 텍스트에서 객관적인 정보를 추출하고, 'extract_objective_analysis' 함수를 사용해서 반환해주세요.
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
        "description": "여러 데이터들을 종합하여, 이 데이터를 업로드한 사용자에 대한 프로파일링 결과를 생성합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "creative_profiling_results": {
                    "type": "object",
                    "properties": {
                        "inferred_user_interests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "데이터를 종합하여 추론한 사용자의 잠재적 관심사 목록. 반드시 입력 데이터의 언어로 작성해야 합니다."
                        },
                        "new_tag_suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "사용자에게 새롭게 제안할 수 있는 창의적 태그 목록. 반드시 입력 데이터의 언어로 작성하며, 해시태그 형태 권장."
                        },
                        "profiler_summary": {
                            "type": "string",
                            "description": "사용자의 관심사와 취향에 대한 간단한 요약. 반드시 입력 데이터의 언어로 작성해야 합니다."
                        }
                    },
                    "required": ["inferred_user_interests", "new_tag_suggestions", "profiler_summary"]
                }
            },
            "required": ["creative_profiling_results"]
        }
    }
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
                    "당신은 핸드폰 스크린샷에서 추출된 객관적 데이터를 종합하여, "
                    "사용자의 숨겨진 의도와 관심사를 추론하는 창의적인 프로파일러입니다. "
                    "주어진 데이터의 핵심 패턴과 문화적 맥락을 깊이 있게 분석하고, "
                    "모든 출력값(항목명, 요약문, 키워드, 태그 등 모든 텍스트)은 반드시 입력된 OCR 텍스트와 동일한 언어로 작성해야 하며, 영어 단어나 번역을 포함하지 마세요."
                )
            },
            {
                "role": "user",
                "content": (
                    "다음 분석 결과들을 종합하여 하나의 창의적인 프로필을 생성해주세요. "
                    "반복되는 주제나 개체를 선호하고, 일회성 노이즈는 무시하세요. "
                    "출력은 반드시 입력 OCR 텍스트와 동일한 언어로 작성해야 합니다. 한국어 OCR이면 한국어로만, 영어 OCR이면 영어로만 작성하세요. 두 언어를 섞지 마세요."
                    + json.dumps({"objective_data_points": objective_data_points}, ensure_ascii=False)
                )
            }
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