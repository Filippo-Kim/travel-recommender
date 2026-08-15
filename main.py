# -*- coding: utf-8 -*-
"""
국내 여행지 추천 프로그램
LLM API(Gemini) + 지도 API(Kakao Local)를 조합하여
여행 날짜 기준 추천 지역, 맛집 정보, 최종 리포트를 생성한다.
"""

import argparse
import json
import sys
from datetime import datetime

import requests

import gemini_api
import kakao_api


# ===== CLI =====
def parse_args():
    """CLI 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="입력한 날짜에 맞는 국내 여행지를 추천하고 리포트를 생성합니다.",
        epilog='사용 예시: python main.py -date "2026-10-15"'
    )
    parser.add_argument(
        "-date",
        required=True,
        help="여행 날짜 (형식: YYYY-MM-DD)"
    )
    return parser.parse_args()


def validate_date(date_str):
    """날짜 문자열이 YYYY-MM-DD 형식인지 검증한다."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def print_usage_and_exit(date_str):
    """날짜 형식이 잘못된 경우 사용법을 출력하고 종료한다."""
    print(f"[오류] 날짜 형식이 올바르지 않습니다: '{date_str}'")
    print("       올바른 형식: YYYY-MM-DD")
    print('       사용법: python main.py -date "2026-10-15"')
    sys.exit(1)


# ===== 환경 검사 =====
def check_api_keys():
    """API 키가 설정되어 있는지 확인한다. 없으면 안내 후 즉시 종료한다."""
    missing = []
    if not gemini_api.GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not kakao_api.KAKAO_API_KEY:
        missing.append("KAKAO_REST_API_KEY")

    if not missing:
        return

    print(f"[오류] 다음 API 키가 설정되지 않았습니다: {', '.join(missing)}")
    print()
    print("  설정 방법 1) 프로젝트 루트에 .env 파일을 만들고 아래 형식으로 입력")
    print("      GEMINI_API_KEY=발급받은_키")
    print("      KAKAO_REST_API_KEY=발급받은_키")
    print()
    print("  설정 방법 2) 터미널 환경변수로 지정 (현재 세션에만 적용)")
    print('      export GEMINI_API_KEY="발급받은_키"')
    print('      export KAKAO_REST_API_KEY="발급받은_키"')
    sys.exit(1)


# ===== 파이프라인 단계 =====
def step_recommend(travel_date, errors):
    """1단계: LLM으로 여행지 1차 추천을 받는다. 실패하면 프로그램을 종료한다."""
    print("[1/3] 여행지 추천 중...")
    try:
        recommendation = gemini_api.get_recommendation(travel_date)
    except (ValueError, requests.RequestException) as e:
        message = f"1차 추천 생성 실패: {e}"
        errors.append(message)
        print(f"[오류] {message}")
        print("       추천 지역이 없으면 이후 단계를 진행할 수 없어 종료합니다.")
        sys.exit(1)

    print(f"      추천 지역: {recommendation['recommended_city']}")
    return recommendation


def step_search_restaurants(city, errors):
    """2단계: 지도 API로 맛집을 검색한다. 실패해도 빈 리스트로 계속 진행한다."""
    print(f"[2/3] '{city}' 맛집 검색 중...")
    try:
        restaurants = kakao_api.search_restaurants(city, size=5)
    except (ValueError, requests.RequestException) as e:
        message = f"맛집 검색 실패: {e}"
        errors.append(message)
        print(f"      [경고] {message}")
        print("      맛집 섹션은 '데이터 없음'으로 처리하고 계속 진행합니다.")
        return []

    if not restaurants:
        message = f"'{city}' 맛집 검색 결과 0건"
        errors.append(message)
        print(f"      [경고] {message}")
    else:
        print(f"      맛집 {len(restaurants)}곳 확보")

    return restaurants


# ===== 메인 흐름 =====
def main():
    args = parse_args()

    if not validate_date(args.date):
        print_usage_and_exit(args.date)

    check_api_keys()

    travel_date = args.date

    # 각 단계에서 발생한 오류를 모아두는 리스트 (리포트의 errors 섹션에 사용)
    errors = []

    print(f"[시작] 여행 날짜: {travel_date}")

    # --- 1차 추천 ---
    recommendation = step_recommend(travel_date, errors)

    # --- 맛집 검색: 1차 추천 결과를 입력으로 사용 ---
    restaurants = step_search_restaurants(
        recommendation["recommended_city"], errors
    )

    # --- 6단계에서 구현: 최종 리포트 생성 ---
    print("[3/3] 리포트 생성 중... (미구현)")

    # 연결이 잘 됐는지 확인용 출력 (7단계에서 파일 저장으로 대체 예정)
    raw_data = {
        "date": travel_date,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }
    print("\n[중간 확인] 수집된 원본 데이터")
    print(json.dumps(raw_data, ensure_ascii=False, indent=2))

    print(f"\n[완료] 오류 {len(errors)}건")


if __name__ == "__main__":
    main()