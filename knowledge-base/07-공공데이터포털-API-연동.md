# 07. 공공데이터포털(data.go.kr) 검색 서비스 API 연동

## 서비스 개요

| 항목 | 내용 |
|---|---|
| 데이터명 | 공공데이터활용지원센터_공공데이터포털 검색 서비스 |
| 서비스 유형 | REST |
| 심의여부 | 자동승인 |
| 일 호출 제한 | 10,000회 |
| 신청유형 | 개발계정 \| 활용신청 |
| 데이터 포맷 | JSON + XML |
| Base URL | `api.odcloud.kr/api` |
| Swagger | `https://infuser.odcloud.kr/api/stages/43698/api-docs` |
| 서비스 ID | `15077093` |

**용도**: 이 API는 공공데이터포털에 등록된 **데이터셋 목록 자체를 검색**하는 메타 검색 API입니다
(실제 통계값을 주는 API가 아니라 "어떤 데이터셋이 존재하는지"를 찾는 API). 즉
`02-데이터-제공기관-지도.md`를 실데이터로 채우거나, 아이디어 기획 단계에서 "이 기관에 이런
이름의 데이터셋이 실제로 있는지" 빠르게 확인하는 용도로 가장 유용합니다.

## 인증

- 헤더 방식: `Authorization: Infuser <인증키>`
- 쿼리 방식: `?serviceKey=<인증키>` (인코딩된 키 그대로 사용)
- 인증키는 **`.env`의 `ODCLOUD_API_KEY`에만 저장** — 절대 마크다운/코드/커밋 메시지에 원문 노출 금지
  (`.gitignore`에 `.env`가 등록되어 있는지 항상 확인)

## 엔드포인트 3종

| Method | Path | 설명 |
|---|---|---|
| GET | `/{serviceId}/v1/file-data-list` | 파일 형태 데이터 목록 조회 |
| GET | `/{serviceId}/v1/open-data-list` | 오픈API 형태 데이터 목록 조회 |
| GET | `/{serviceId}/v1/dataset` | 데이터셋 조회 |

### 공통 파라미터

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `page` | integer | 페이지 인덱스 (기본값 1) |
| `perPage` | integer | 페이지 크기 (기본값 10) |
| `returnType` | string | 응답 데이터 타입 (기본 JSON, XML 가능) |
| `cond[list_title::LIKE]` | string | 목록명 LIKE 검색 — 보통 **제공기관명**으로 검색 |
| `cond[title::LIKE]` | string | 데이터명 LIKE 검색 — **주제어**로 검색 |
| `cond[created_at::LT]` | string | 등록일 조건 |

### 응답 코드

| 코드 | 의미 |
|---|---|
| 200 | 성공 (`page`, `perPage`, `totalCount`, `list_title`, `update_cycle`, `created_at`, `id`, `media_type`, `media_cnt`, `ext` 등 필드 포함) |
| 401 | 인증 정보가 정확하지 않음 |
| 500 | API 서버 오류 |

## 사용법 — `scripts/odcloud_search.py`

```bash
# 사전 준비: 저장소 루트 .env에 ODCLOUD_API_KEY 설정 (완료됨, git엔 없음)

# 키워드(기관명/주제어)로 오픈API 목록 검색
python3 scripts/odcloud_search.py --endpoint open-data-list --keyword "한국무역보험공사"

# 파일형 데이터 검색
python3 scripts/odcloud_search.py --endpoint file-data-list --keyword "석유" --per-page 20

# 데이터셋 자체 검색
python3 scripts/odcloud_search.py --endpoint dataset --keyword "탄소배출권"

# 20개 주관기관 전체 일괄 조회 (knowledge-base/data/institutions.json 기반)
# → 결과가 knowledge-base/data/odcloud/<기관명>.json 으로 저장됨 (.gitignore 처리, 커밋 안 됨)
python3 scripts/odcloud_search.py --batch
```

## ⚠️ 알려진 제약 — 이 세션(샌드박스)에서는 호출 실패함

이 지식베이스를 구축한 클라우드 실행 환경은 조직 아웃바운드 네트워크 정책상
`api.odcloud.kr`로의 HTTPS 연결이 차단되어 있습니다(프록시 로그: `connect_rejected`,
`gateway answered 403 to CONNECT`). 이는 **API 키나 코드의 문제가 아니라 이 세션의 네트워크
정책 문제**이며, 조직 정책 차단은 재시도하지 않는 것이 원칙이라 이 세션에서는 더 이상 시도하지
않았습니다.

**해결 방법**:
1. 로컬 PC, 또는 이 도메인이 허용된 다른 네트워크 환경에서 `python3 scripts/odcloud_search.py --batch`
   실행 → `knowledge-base/data/odcloud/`에 실데이터 저장
2. 그 결과를 다시 이 프로젝트(Claude Code 세션)에 알려주면 `02-데이터-제공기관-지도.md`를
   실데이터 기준으로 갱신
3. 또는 Claude Code 웹 환경 설정에서 이 세션의 네트워크 정책(허용 도메인)에 `api.odcloud.kr`을
   추가할 수 있는지 확인 — 환경 설정 방법은 https://code.claude.com/docs/en/claude-code-on-the-web 참고

## 이 API로 검증해야 할 것 (우선순위)

`05-수상패턴분석.md`의 블루오션 매트릭스에서 제안한 미활용 기관들의 데이터가 **실제로 존재하는지**를
이 API로 검증하는 것이 다음 최우선 작업입니다:

```bash
python3 scripts/odcloud_search.py --endpoint open-data-list --keyword "한국무역보험공사"
python3 scripts/odcloud_search.py --endpoint open-data-list --keyword "한국로봇산업진흥원"
python3 scripts/odcloud_search.py --endpoint open-data-list --keyword "강원랜드"
python3 scripts/odcloud_search.py --endpoint open-data-list --keyword "한국가스안전공사"
```
