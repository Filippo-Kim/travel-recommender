# 국내 여행지 추천 프로그램

여행 날짜를 입력하면 **LLM API가 여행지를 추천**하고, **지도 API로 해당 지역의 맛집을 검색**한 뒤, 두 결과를 조합하여 **최종 여행 리포트를 생성**하는 CLI 프로그램입니다.

---

## 1. 프로그램 개요

### 동작 흐름

```
날짜 입력 (-date)
      ↓
[1] Gemini API → 추천 도시 / 날씨 / 행사 / 추천 이유 (JSON)
      ↓  recommended_city 를 다음 단계 검색어로 전달
[2] Kakao Local API → 해당 도시의 맛집 5곳 (이름/주소/분류/좌표/링크)
      ↓  [1] + [2] 결과를 함께 전달
[3] Gemini API → 최종 여행 리포트 (Markdown)
      ↓
results/ 폴더에 원본 JSON + 리포트 저장
```

단일 API 호출이 아니라, **앞 단계의 출력이 뒤 단계의 입력이 되는 파이프라인** 구조입니다.
1단계에서 LLM에게 굳이 JSON 형식을 요구하는 이유도 여기에 있습니다. 사람이 읽을 문장이 아니라 다음 단계 코드가 파싱할 데이터여야 하기 때문입니다.

### 사용 API

| 구분 | 서비스 | 모델 / 엔드포인트 |
| --- | --- | --- |
| LLM | Google Gemini | `gemini-3.5-flash` |
| 지도/장소 | Kakao Local | 키워드 검색 (`/v2/local/search/keyword.json`) |

### 파일 구조

```
travel-recommender/
├── main.py            # CLI 진입점, 파이프라인 제어, 결과 저장
├── gemini_api.py      # LLM 연동 (1차 추천 JSON + 최종 리포트)
├── kakao_api.py       # 지도 API 연동 (맛집 검색)
├── requirements.txt   # 의존 패키지
├── .env               # API 키 (git 추적 제외)
├── .env.example       # 키 설정 견본
├── .gitignore
└── results/           # 실행 결과물 (자동 생성)
    ├── YYYY-MM-DD_raw.json
    └── YYYY-MM-DD_report.md
```

---

## 2. 실행 방법

### 사전 요구사항

- Python 3.10 이상

### 설치

```bash
git clone https://github.com/Filippo-Kim/travel-recommender.git
cd travel-recommender

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 실행

```bash
python main.py -date "2026-10-15"
```

| 옵션 | 필수 | 설명 |
| --- | --- | --- |
| `-date` | O | 여행 날짜 (`YYYY-MM-DD` 형식) |
| `--no-cache` | X | 저장된 결과를 무시하고 API를 다시 호출 |

날짜 형식이 올바르지 않으면 사용법을 출력하고 종료합니다.

```bash
$ python main.py -date "2026/10/15"
[오류] 날짜 형식이 올바르지 않습니다: '2026/10/15'
       올바른 형식: YYYY-MM-DD
       사용법: python main.py -date "2026-10-15"
```

### 실행 예시

```
[시작] 여행 날짜: 2026-10-15
[1/3] 여행지 추천 중...
      추천 지역: 경주
[2/3] '경주' 맛집 검색 중...
      맛집 5곳 확보
[3/3] 리포트 생성 중...
      리포트 생성 완료

[완료] 오류 0건
       원본 데이터: results/2026-10-15_raw.json
       최종 리포트: results/2026-10-15_report.md
```

---

## 3. API 키 설정 방법

### 3-1. 키 발급

**Gemini API 키**

1. [Google AI Studio](https://aistudio.google.com/apikey) 접속 후 Google 계정으로 로그인
2. `API 키 만들기` 클릭
3. 발급된 키 복사

**Kakao REST API 키**

1. [Kakao Developers](https://developers.kakao.com) 접속 후 로그인
2. `내 애플리케이션` → `애플리케이션 추가하기`
3. 생성한 앱 → `앱 키` → **REST API 키** 복사
4. `제품 설정` → `카카오맵` → **활성화 설정 ON**
   (이 설정을 켜지 않으면 `NotAuthorizedError: disabled OPEN_MAP_AND_LOCAL service` 오류가 발생합니다)

### 3-2. 키 등록

프로젝트 루트에 `.env` 파일을 만들고 아래 형식으로 입력합니다.
`.env.example` 파일을 복사해서 사용하면 편합니다.

```bash
cp .env.example .env
```

```dotenv
GEMINI_API_KEY=발급받은_Gemini_키
KAKAO_REST_API_KEY=발급받은_Kakao_REST_키
```

환경변수로 지정해도 동작합니다. (현재 터미널 세션에만 적용)

```bash
# macOS / Linux
export GEMINI_API_KEY="발급받은_키"
export KAKAO_REST_API_KEY="발급받은_키"
```

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="발급받은_키"
$env:KAKAO_REST_API_KEY="발급받은_키"
```

키가 설정되지 않은 상태로 실행하면 즉시 종료되며 설정 방법을 안내합니다.

---

## 4. 보안 주의사항

- **API 키를 코드에 직접 작성하지 않습니다.** 모든 키는 `.env` 또는 환경변수에서 읽어옵니다.
- `.env`는 `.gitignore`에 등록되어 있어 Git에 커밋되지 않습니다.
- `.env.example`에는 **실제 키 값이 아닌 자리표시자만** 작성합니다.
- 실행 로그와 결과 파일(`results/`)에는 키가 기록되지 않습니다.
- 실수로 키를 커밋했다면 파일 수정만으로는 커밋 이력에 남으므로, **발급처에서 키를 재발급**해야 합니다.

키를 코드가 아닌 외부에 두는 이유는 다음과 같습니다.

- 협업이나 저장소 공개 시 키가 노출되는 사고를 막습니다.
- 키를 교체할 때 코드를 수정할 필요가 없습니다.
- 과금·쿼터가 걸린 서비스에서 무단 사용 사고를 예방합니다.

---

## 5. 결과물 확인 방법

실행이 끝나면 `results/` 폴더에 두 개의 파일이 생성됩니다.
파일명은 입력한 여행 날짜를 기준으로 하며, 같은 날짜로 재실행하면 덮어써집니다.

### `YYYY-MM-DD_raw.json` — 원본 데이터

```json
{
  "date": "2026-10-15",
  "generated_at": "2026-08-15T14:30:52",
  "recommendation": {
    "recommended_city": "경주",
    "weather": "선선하고 맑은 날이 많습니다.",
    "events": ["신라문화제"],
    "reason": "가을 단풍과 유적지가 어우러지는 시기입니다."
  },
  "restaurants": [
    {
      "name": "○○식당",
      "address": "경상북도 경주시 ...",
      "category": "음식점 > 한식",
      "url": "http://place.map.kakao.com/...",
      "x": 129.21,
      "y": 35.84
    }
  ],
  "errors": []
}
```

### `YYYY-MM-DD_report.md` — 최종 리포트

아래 항목이 포함된 Markdown 문서입니다.

- 추천 지역과 추천 이유
- 날씨
- 행사 및 축제
- 맛집 리스트 (검색 결과가 0건이면 `데이터 없음`)
- 1일 추천 일정 (오전 / 오후 / 저녁)
- 실행 중 오류가 있었다면 하단에 오류 요약 섹션

VS Code에서 `⌘ + Shift + V` (Windows: `Ctrl + Shift + V`)로 미리보기할 수 있습니다.

---

## 6. 에러 처리 정책

| 상황 | 동작 |
| --- | --- |
| API 키 미설정 | 즉시 종료 + 설정 방법 안내 |
| 날짜 형식 오류 | 사용법 출력 후 종료 |
| LLM JSON 파싱 실패 | 더 엄격한 프롬프트로 **1회만** 재요청 (총 2회, 무한 재시도 없음) |
| 1차 추천 최종 실패 | 추천 지역 없이는 진행 불가하므로 종료 |
| 지도 API 실패 / 결과 0건 | 맛집 섹션을 `데이터 없음`으로 처리하고 **리포트 생성은 계속 진행** |
| 리포트 생성 실패 | 수집된 데이터로 LLM 없이 기본 리포트를 자동 구성 |

발생한 오류는 내부 `errors` 리스트에 누적되어 원본 JSON의 `errors` 배열과 리포트 하단 섹션에 기록됩니다. 오류가 없으면 빈 배열로 저장됩니다.

---

## 7. 보너스 과제: 결과 캐싱

같은 `-date`로 재실행하면 저장된 원본 JSON을 읽어 **추천·맛집 검색 API 호출을 건너뜁니다.**

```bash
$ python main.py -date "2026-10-15"
[시작] 여행 날짜: 2026-10-15
[캐시] 저장된 결과를 발견하여 API 호출을 건너뜁니다.
       새로 조회하려면 --no-cache 옵션을 사용하세요.
[1/3] 여행지 추천 (캐시): 경주
[2/3] 맛집 검색 (캐시): 5곳
[3/3] 리포트 생성 중...
```

캐시가 고정하는 것은 **입력 데이터**(추천 도시, 맛집 목록)이며, 리포트는 매번 새로 생성됩니다.
캐시를 무시하고 처음부터 다시 조회하려면 `--no-cache` 옵션을 사용합니다.

```bash
python main.py -date "2026-10-15" --no-cache
```

캐시 파일이 손상되었거나 형식이 맞지 않으면 경고를 출력하고 정상적으로 API를 호출합니다.