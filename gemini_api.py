# -*- coding: utf-8 -*-
"""
Gemini API 연동 모듈
1차 추천(여행지/날씨/행사)을 JSON 형태로 생성한다.
"""

import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-flash-latest"
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
    print("\n[파싱된 원본 JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))