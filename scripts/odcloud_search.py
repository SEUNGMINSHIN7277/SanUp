#!/usr/bin/env python3
"""공공데이터포털(data.go.kr) 검색 서비스 API 클라이언트.

서비스: 공공데이터활용지원센터_공공데이터포털 검색 서비스 (odcloud.kr, 서비스ID 15077093)
용도: 산업통상부 및 산하기관 데이터셋을 키워드/제공기관명으로 검색해
      knowledge-base/02-데이터-제공기관-지도.md 를 실데이터로 채우는 데 사용한다.

사전 준비: 저장소 루트의 .env 에 ODCLOUD_API_KEY 설정 (git에는 커밋되지 않음, .gitignore 확인)

사용 예:
  python3 scripts/odcloud_search.py --endpoint open-data-list --keyword 한국무역보험공사
  python3 scripts/odcloud_search.py --endpoint file-data-list --keyword 석유 --per-page 20
  python3 scripts/odcloud_search.py --endpoint dataset --keyword 탄소배출권
  python3 scripts/odcloud_search.py --batch          # institutions.json 20개 기관 전체 일괄 조회 후 저장

주의: 샌드박스/CI 환경의 아웃바운드 네트워크 정책에 따라 api.odcloud.kr 접근이
차단될 수 있다(조직 egress 정책 403). 그 경우 로컬 PC 등 일반 네트워크 환경에서
실행할 것 — 코드 자체는 정상이며 네트워크 도달성만 문제다.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINTS = {"file-data-list": "file-data-list", "open-data-list": "open-data-list", "dataset": "dataset"}


def load_dotenv(path=None):
    path = path or os.path.join(REPO_ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def search(endpoint, keyword=None, title=None, page=1, per_page=10,
           api_key=None, service_id=None, base_url=None, timeout=15):
    base_url = base_url or os.environ.get("ODCLOUD_BASE_URL", "https://api.odcloud.kr/api")
    service_id = service_id or os.environ.get("ODCLOUD_SERVICE_ID", "15077093")
    api_key = api_key or os.environ.get("ODCLOUD_API_KEY")
    if not api_key:
        raise SystemExit("ODCLOUD_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요 (.env.example 참고).")

    path = ENDPOINTS.get(endpoint)
    if not path:
        raise SystemExit(f"알 수 없는 endpoint: {endpoint} (가능: {', '.join(ENDPOINTS)})")

    params = {"page": page, "perPage": per_page, "returnType": "JSON"}
    if keyword:
        params["cond[list_title::LIKE]"] = keyword
    if title:
        params["cond[title::LIKE]"] = title

    url = f"{base_url}/{service_id}/v1/{path}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = urllib.request.Request(url, headers={"Authorization": f"Infuser {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"네트워크 오류(방화벽/프록시 egress 정책일 수 있음): {e.reason}")


def run_batch(per_page=10, sleep_sec=0.3):
    inst_path = os.path.join(REPO_ROOT, "knowledge-base", "data", "institutions.json")
    with open(inst_path, encoding="utf-8") as f:
        institutions = json.load(f)["institutions"]

    out_dir = os.path.join(REPO_ROOT, "knowledge-base", "data", "odcloud")
    os.makedirs(out_dir, exist_ok=True)

    summary = []
    for inst in institutions:
        name = inst["name"]
        try:
            result = search("open-data-list", keyword=name, per_page=per_page)
            out_path = os.path.join(out_dir, f"{name}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            count = result.get("totalCount", "?")
            print(f"[OK] {name}: totalCount={count} -> {out_path}")
            summary.append({"institution": name, "status": "ok", "totalCount": count})
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            summary.append({"institution": name, "status": "fail", "error": str(e)})
        time.sleep(sleep_sec)

    with open(os.path.join(out_dir, "_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n배치 완료: {out_dir}/_summary.json 참고")


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="공공데이터포털 검색 서비스 API 클라이언트")
    parser.add_argument("--endpoint", choices=list(ENDPOINTS), default="open-data-list")
    parser.add_argument("--keyword", help="목록명(list_title) LIKE 검색어 - 보통 제공기관명/주제어")
    parser.add_argument("--title", help="데이터명(title) LIKE 검색어")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=10)
    parser.add_argument("--batch", action="store_true", help="institutions.json 20개 기관 일괄 조회")
    args = parser.parse_args()

    if args.batch:
        run_batch(per_page=args.per_page)
        return

    try:
        result = search(args.endpoint, keyword=args.keyword, title=args.title,
                         page=args.page, per_page=args.per_page)
    except RuntimeError as e:
        raise SystemExit(str(e))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
