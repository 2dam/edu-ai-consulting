"""
collect_academies.py — 전국 학원 리스트 수집 → CurriculumItem 으로 ingest

출처: data.go.kr 학원신고현황 (시·도별 교육청 공공 OpenAPI)
예: "서울특별시 학원및교습소신고현황", "경기도 학원신고현황" 등 수백 개의 별도 OpenAPI.
각 OpenAPI는 data.go.kr 발급 인증키(DATA_API_KEY) + 시도별 endpoint 가 다름.

이 스크립트는:
  1. 시도별 endpoint 목록(하단 ACADEMY_APIS)을 순회
  2. 각 OpenAPI를 호출해 학원 목록(JSON)을 받음
  3. 레코드를 IngestPayload(CurriculumItem) 형태로 변환
  4. ingest_client 를 통해 /ingest-batch 로 밀어넣음

⚠️ 법적 주의:
  - 학원정보는 영리 목적 무단 스크래핑 시 문제 소지 있음. 공공데이터 개방 문서(Guide)의
    이용조건(상업적 이용 가능 여부, 출처 표기)을 사전 확인할 것.
  - 요청 빈도(rate limit)를 지켜야 함 — DEFAULT_DELAY 적용.

실행(예):
  DATA_API_KEY=xxxx python collect_academies.py --limit 1000
  DATA_API_KEY=xxxx python collect_academies.py --only seoul --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import requests

# IngestPayload.item_type 값 (/site-stats 가 세는 값과 일치)
ITEM_TYPE = "CurriculumItem"

# 호출 간 지연(초) — 공공 API rate limit 존중
DEFAULT_DELAY = 0.3

# ── 시도별 학원신고현황 OpenAPI endpoint 예시 ───────────────────────────────
# 실제 endpoint 는 data.go.kr 에서 각 시도별 "학원신고현황" 검색 후 확정 필요.
# 아래는 플레이스홀더(실제 키 발급 후 채울 것). key-name 은 보통 'serviceKey'.
ACADEMY_APIS: dict[str, str] = {
    "seoul": "https://api.odcloud.go.kr/api/15088002/v1/uddi:xxxx-seoul-academy",
    "gyeonggi": "https://api.odcloud.go.kr/api/15088002/v1/uddi:xxxx-gyeonggi-academy",
    # ... 나머지 시도는 data.go.kr 에서 검색해 채울 것
}

# data.go.kr 표준 응답 래퍼 키 (실제 API마다 상이 — 샘플로 확인 후 조정)
RESPONSE_DATA_KEY = "data"          # 예: response.data 또는 data
ROWS_KEY = "rows"                     # 목록 배열 키 (API별 다름 → 샘플로 확인)
TOTAL_KEY = "totalCount"            # 전체 건수 키


def log(*a: Any) -> None:
    print("[collect_academies]", *a, file=sys.stderr, flush=True)


def _field(row: dict, *candidates: str, default: Any = None) -> Any:
    """API별 필드명 차이를 흡수하기 위한 안전 getter."""
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return default


def fetch_page(base_url: str, api_key: str, page: int, per_page: int) -> dict:
    params = {
        "serviceKey": api_key,
        "page": page,
        "perPage": per_page,
        # 일부 API는 returnType=JSON 요구
        "returnType": "JSON",
    }
    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_rows(payload: dict) -> list[dict]:
    """다양한 응답 구조에서 레코드 배열을 추출."""
    if RESPONSE_DATA_KEY in payload and isinstance(payload[RESPONSE_DATA_KEY], dict):
        inner = payload[RESPONSE_DATA_KEY]
        if ROWS_KEY in inner:
            return inner[ROWS_KEY]
    if ROWS_KEY in payload:
        return payload[ROWS_KEY]
    if isinstance(payload.get("data"), list):
        return payload["data"]
    return []


def to_payload(region: str, row: dict) -> dict:
    """학원 1건 → IngestPayload(CurriculumItem) 매핑."""
    name = _field(row, "agrdeName", "academy_name", "학원명", "name")
    addr = _field(row, "address", "주소", "siteWhlAddr", "roadAddr")
    subject = _field(row, "subject", "과목", "lessonSubject")
    return {
        "item_type": ITEM_TYPE,
        "data": {
            "source_url": _field(row, "source_url", "gccampSrvcSttgUrl", default=""),
            "facility_type": "academy",
            "region": region,
            "district": _field(row, "district", "시군구", "signguNm", default=""),
            "name": name or "",
            "address": addr or "",
            "subject": subject or "",
            "collected_at": _field(row, "collected_at", default=time.strftime("%Y-%m-%d")),
        },
    }


def collect_region(region: str, base_url: str, api_key: str, limit: int, dry_run: bool) -> Iterable[dict]:
    page = 1
    collected = 0
    per_page = 100
    while collected < limit:
        try:
            payload = fetch_page(base_url, api_key, page, per_page)
        except Exception as e:  # noqa: BLE001
            log(f"[{region}] page {page} fetch 실패: {e}")
            break
        rows = parse_rows(payload)
        if not rows:
            break
        for row in rows:
            if collected >= limit:
                break
            yield to_payload(region, row)
            collected += 1
        if len(rows) < per_page:
            break
        page += 1
        time.sleep(DEFAULT_DELAY)
        if dry_run:
            break  # dry-run 은 1페이지만


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.getenv("DATA_API_KEY", ""), help="data.go.kr 인증키")
    ap.add_argument("--only", default=None, help="특정 시도만 (예: seoul)")
    ap.add_argument("--limit", type=int, default=10_000, help="시도당 최대 수집 건수")
    ap.add_argument("--dry-run", action="store_true", help="수집만 하고 ingest 는 안 함")
    args = ap.parse_args()

    if not args.api_key:
        log("DATA_API_KEY 가 필요합니다. (--api-key 또는 env)")
        sys.exit(2)
    if not ACADEMY_APIS:
        log("ACADEMY_APIS 가 비어있음 — data.go.kr 에서 시도별 endpoint 를 채우세요.")
        sys.exit(2)

    targets = {args.only: ACADEMY_APIS[args.only]} if args.only else ACADEMY_APIS

    # ingest_client 가 있으면 import, 없으면 stdout JSONL 출력
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from ingest_client import push_batch  # type: ignore
        pusher = push_batch
    except Exception:  # noqa: BLE001
        pusher = None

    total = 0
    buffer: list[dict] = []
    BATCH = 100

    for region, url in targets.items():
        log(f"[{region}] 수집 시작 (limit={args.limit})")
        for p in collect_region(region, url, args.api_key, args.limit, args.dry_run):
            total += 1
            if args.dry_run:
                print(json.dumps(p, ensure_ascii=False))
                continue
            buffer.append(p)
            if len(buffer) >= BATCH:
                if pusher:
                    pusher(buffer)
                else:
                    print(json.dumps(buffer, ensure_ascii=False))
                buffer = []
        if buffer and not args.dry_run:
            if pusher:
                pusher(buffer)
            else:
                print(json.dumps(buffer, ensure_ascii=False))
            buffer = []
        log(f"[{region}] 누적 {total}건")

    log(f"완료 — 총 {total}건" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
