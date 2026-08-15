# -*- coding: utf-8 -*-
"""
Gemini API 연동 모듈
1) 1차 추천(여행지/날씨/행사)을 JSON 형태로 생성한다.
2) 1차 추천 + 맛집 목록을 받아 최종 여행 리포트를 Markdown으로 생성한다.
"""

import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)

# 1차 추천에서 반드시 있어야 하는 키
REQUIRED_KEYS = ["recommended_city", "weather", "events", "reason"]


def call_gemini(prompt):
    """
    Gemini에 프롬프트를 보내고 응답 텍스트를 돌려준다.

    Raises:
        ValueError: API 키 미설정 또는 응답에 텍스트가 없는 경우
        requests.RequestException: 네트워크/인증/쿼터 오류
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    response = requests.post(
        GEMINI_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini 응답에 candidates가 없습니다.")

    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if "text" in part]
    if not texts:
        raise ValueError("Gemini 응답에 텍스트가 없습니다.")

    return "".join(texts).strip()


# ===== 1차 추천 =====
def extract_json(text):
    """
    LLM 응답 텍스트에서 JSON 부분만 뽑아 파싱한다.
    ```json ... ``` 코드펜스나 앞뒤 설명이 붙어 있어도 처리한다.

    Raises:
        json.JSONDecodeError: 파싱에 실패한 경우
    """
    cleaned = text.strip()

    # ```json ... ``` 또는 ``` ... ``` 코드펜스 제거
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    # 앞뒤에 설명이 붙은 경우 첫 { 부터 마지막 } 까지만 사용
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and start < end:
        cleaned = cleaned[start:end + 1]

    return json.loads(cleaned)


def build_recommend_prompt(date):
    """1차 추천용 프롬프트를 만든다."""
    return f"""너는 국내 여행 전문가야. {date}에 여행하기 좋은 대한민국 국내 도시 한 곳을 추천해줘.

아래 형식의 JSON만 출력해. 설명, 인사말, 마크다운 코드블록 표시는 절대 붙이지 마.

{{
  "recommended_city": "도시명 (예: 제주, 강릉, 경주)",
  "weather": "해당 시기의 일반적인 날씨를 한 문장으로",
  "events": ["그 시기에 열리는 행사나 축제 이름", "최대 3개까지"],
  "reason": "추천 이유를 2~4문장으로"
}}

조건:
- recommended_city는 지도 검색에 쓸 수 있도록 짧은 도시명으로만 작성한다.
- events는 문자열 배열이며, 마땅한 행사가 없으면 빈 배열 []로 둔다.
- 모든 값은 한국어로 작성한다."""


def build_retry_prompt(date):
    """JSON 파싱 실패 시 사용할 더 엄격한 재요청 프롬프트."""
    return f"""{date} 기준 대한민국 국내 여행지 추천 결과를 JSON으로만 출력해.

다른 텍스트는 한 글자도 쓰지 말고, 아래 4개 키만 가진 JSON 객체 하나만 출력해.

recommended_city: 문자열
weather: 문자열
events: 문자열 배열
reason: 문자열"""


def validate_recommendation(data):
    """필수 키와 타입을 검증한다."""
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"필수 키 누락: {missing}")

    if not isinstance(data["events"], list):
        raise ValueError("events는 배열이어야 합니다.")

    return True


def get_recommendation(date):
    """
    날짜를 받아 1차 추천 JSON을 돌려준다.
    파싱에 실패하면 더 엄격한 프롬프트로 1회만 재시도한다.

    Returns:
        dict: recommended_city / weather / events / reason
    """
    prompts = [
        build_recommend_prompt(date),   # 1차 시도
        build_retry_prompt(date),       # 재시도 1회 (총 2회, 무한 재시도 금지)
    ]

    last_error = None

    for attempt, prompt in enumerate(prompts, start=1):
        raw_text = call_gemini(prompt)
        try:
            data = extract_json(raw_text)
            validate_recommendation(data)
            return data
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            print(f"  [경고] {attempt}차 시도 JSON 처리 실패: {e}")

    raise ValueError(f"1차 추천 JSON 생성 실패 (2회 시도): {last_error}")


# ===== 최종 리포트 =====
def format_restaurants(restaurants):
    """맛집 목록을 프롬프트에 넣을 수 있는 텍스트로 변환한다."""
    if not restaurants:
        return "(검색 결과 없음)"

    lines = []
    for i, place in enumerate(restaurants, start=1):
        lines.append(
            f"{i}. {place['name']} / 주소: {place['address']} / "
            f"분류: {place['category']} / 링크: {place['url']}"
        )
    return "\n".join(lines)


def build_report_prompt(date, recommendation, restaurants):
    """최종 리포트 생성용 프롬프트를 만든다."""
    events = recommendation["events"]
    events_text = ", ".join(events) if events else "(없음)"

    return f"""아래 데이터를 바탕으로 국내 여행 리포트를 마크다운으로 작성해줘.

# 입력 데이터
- 여행 날짜: {date}
- 추천 지역: {recommendation['recommended_city']}
- 추천 이유: {recommendation['reason']}
- 날씨: {recommendation['weather']}
- 행사/축제: {events_text}
- 맛집 목록:
{format_restaurants(restaurants)}

# 작성 규칙
1. 아래 5개 섹션을 이 순서대로 모두 포함한다.
   - 추천 지역과 추천 이유
   - 날씨
   - 행사 및 축제
   - 맛집 리스트
   - 1일 추천 일정
2. 맛집 리스트는 이름, 주소, 분류, 링크를 표 또는 목록으로 정리한다.
   맛집 목록이 "(검색 결과 없음)"이면 해당 섹션에 "데이터 없음"이라고만 적는다.
3. 행사가 "(없음)"이면 해당 섹션에 "예정된 행사 정보 없음"이라고 적는다.
4. 1일 추천 일정은 오전 / 오후 / 저녁 세 구간으로 나누어 작성하고,
   저녁 구간에는 위 맛집 중 한 곳을 넣는다. (맛집이 없으면 지역 특성에 맞게 제안)
5. 입력 데이터에 없는 사실을 지어내지 않는다.
6. 마크다운 본문만 출력하고, 코드블록(```)으로 전체를 감싸지 않는다.
7. 문서 제목은 "# {date} {recommendation['recommended_city']} 여행 리포트" 로 시작한다."""


def strip_outer_fence(text):
    """응답 전체가 코드블록으로 감싸져 있으면 벗겨낸다."""
    stripped = text.strip()
    match = re.fullmatch(r"```(?:markdown|md)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def generate_report(date, recommendation, restaurants):
    """
    1차 추천 + 맛집 목록을 받아 최종 리포트를 Markdown 텍스트로 생성한다.

    Returns:
        str: 마크다운 리포트 본문
    """
    prompt = build_report_prompt(date, recommendation, restaurants)
    raw_text = call_gemini(prompt)
    return strip_outer_fence(raw_text)


# ===== 단독 실행 테스트용 =====
if __name__ == "__main__":
    import sys

    target_date = sys.argv[1] if len(sys.argv) > 1 else "2026-10-15"

    try:
        result = get_recommendation(target_date)
    except ValueError as e:
        print(f"[오류] {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[오류] Gemini API 요청 실패: {e}")
        sys.exit(1)

    print(f"\n입력 날짜: {target_date}")
    print("-" * 40)
    print(f"추천 도시: {result['recommended_city']}")
    print(f"날씨     : {result['weather']}")
    print(f"행사     : {', '.join(result['events']) if result['events'] else '없음'}")
    print(f"추천 이유: {result['reason']}")
    print("-" * 40)

    # 맛집 0건 상황을 가정한 리포트 생성 테스트
    print("\n[리포트 생성 테스트: 맛집 0건 상황]")
    print("=" * 60)
    print(generate_report(target_date, result, []))
    print("=" * 60)