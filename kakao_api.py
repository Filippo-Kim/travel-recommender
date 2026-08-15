# -*- coding: utf-8 -*-
"""
Kakao Local API 연동 모듈
키워드 검색으로 특정 도시의 맛집 정보를 가져온다.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def search_restaurants(city, size=5):
    """
    도시 이름으로 맛집을 검색한다.

    Args:
        city (str): 검색할 도시명 (예: "제주")
        size (int): 가져올 맛집 개수 (1~15)

    Returns:
        list[dict]: 맛집 정보 리스트. 검색 결과가 없으면 빈 리스트.

    Raises:
        ValueError: API 키가 설정되지 않은 경우
        requests.RequestException: 네트워크/인증/쿼터 오류
    """
    if not KAKAO_API_KEY:
        raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")

    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "query": f"{city} 맛집",
        "size": size,
    }

    response = requests.get(
        KAKAO_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()

    documents = response.json().get("documents", [])
    return [normalize_place(doc) for doc in documents]


def normalize_place(doc):
    """카카오 응답 항목을 과제 요구 필드 형태로 정리한다."""
    return {
        "name": doc.get("place_name", ""),
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "category": doc.get("category_name", ""),
        "url": doc.get("place_url", ""),
        "x": to_float(doc.get("x")),  # 경도(longitude)
        "y": to_float(doc.get("y")),  # 위도(latitude)
    }


def to_float(value):
    """문자열 좌표를 숫자로 변환한다. 실패하면 None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ===== 단독 실행 테스트용 =====
if __name__ == "__main__":
    import sys

    target_city = sys.argv[1] if len(sys.argv) > 1 else "제주"

    try:
        places = search_restaurants(target_city)
    except ValueError as e:
        print(f"[오류] {e}")
        print("       .env 파일에 KAKAO_REST_API_KEY를 설정해주세요.")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"[오류] 카카오 API 요청 실패: {e}")
        sys.exit(1)

    print(f"'{target_city}' 맛집 검색 결과: {len(places)}건\n")
    for i, place in enumerate(places, start=1):
        print(f"{i}. {place['name']}")
        print(f"   주소: {place['address']}")
        print(f"   분류: {place['category']}")
        print(f"   좌표: ({place['y']}, {place['x']})")
        print(f"   링크: {place['url']}\n")