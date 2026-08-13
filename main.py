# -*- coding: utf-8 -*-
"""
국내 여행지 추천 프로그램
LLM API(Gemini) + 지도 API(Kakao Local)를 조합하여
여행 날짜 기준 추천 지역, 맛집 정보, 최종 리포트를 생성한다.
"""

import argparse
import sys
from datetime import datetime


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
        help='여행 날짜 (형식: YYYY-MM-DD)'
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
    print('       올바른 형식: YYYY-MM-DD')
    print('       사용법: python main.py -date "2026-10-15"')
    sys.exit(1)


# ===== 메인 흐름 =====
def main():
    args = parse_args()

    if not validate_date(args.date):
        print_usage_and_exit(args.date)

    travel_date = args.date

    # 각 단계에서 발생한 오류를 모아두는 리스트 (리포트의 errors 섹션에 사용)
    errors = []

    print(f"[시작] 여행 날짜: {travel_date}")

    # --- 3단계에서 구현: 지도 API로 맛집 검색 ---
    print("[1/3] 여행지 추천 중... (미구현)")

    # --- 4단계에서 구현: LLM으로 1차 추천 JSON 생성 ---
    print("[2/3] 맛집 검색 중... (미구현)")

    # --- 6단계에서 구현: LLM으로 최종 리포트 생성 ---
    print("[3/3] 리포트 생성 중... (미구현)")

    print(f"[완료] 오류 {len(errors)}건")


if __name__ == "__main__":
    main()