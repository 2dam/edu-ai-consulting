"""유치원알리미(e-childschoolinfo.moe.go.kr) 기본현황(신규) API 전국 크롤.

공공데이터포털 표준 포맷을 쓰는 daycare/academy와 달리 이 API는 자체 인증키
(SNS 로그인 -> 계정 승인) 체계와 자체 응답 포맷(status/kinderInfo)을 쓰기 때문에
early_education_spider.py의 _public_data_request 로는 처리할 수 없다. 시군구 단위
(sidoCode+sggCode) 필수 파라미터라 전국을 돌리려면 시군구코드 목록을 순회해야 한다.

사용법:
    CHILD_SCHOOL_INFO_KEY=<발급받은 인증키> python kindergarten_crawl.py [--export-url URL] [--dry-run]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

API_URL = "https://e-childschoolinfo.moe.go.kr/api/notice/basicInfo2.do"
SGG_CODES_FILE = Path(__file__).parent / "sgg_codes.json"
PAGE_SIZE = 100
REQUEST_DELAY = 1.0  # 초당 요청 부담 완화
BATCH_SIZE = 50


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def map_item(row, sido_name, district_name, now):
    ppcnt = sum(
        to_int(row.get(k)) or 0
        for k in ("ppcnt3", "ppcnt4", "ppcnt5", "mixppcnt", "shppcnt")
    )
    return {
        "source_url": f"{API_URL}?sidoCode={row.get('_sidoCode')}&sggCode={row.get('_sggCode')}",
        "facility_type": "kindergarten",
        "name": row.get("kindername", ""),
        "region": sido_name,
        "district": district_name,
        "address": row.get("addr", ""),
        "lat": float(row["lttdcdnt"]) if row.get("lttdcdnt") else None,
        "lng": float(row["lngtcdnt"]) if row.get("lngtcdnt") else None,
        "establishment_type": row.get("establish", ""),
        "capacity": None,  # 이 API(기본현황)에는 정원 필드가 없음 — 지어내지 않음
        "current_enrollment": ppcnt or None,
        "teacher_count": None,
        "evaluation_grade": "",  # 유치원평가 결과는 이 API 범위 밖
        "status_note": f"{row.get('telno', '')} · {row.get('opertime', '')}".strip(" ·"),
        "crawled_at": now,
    }


def fetch_region(session, key, sgg_code, sido_name, district_name):
    now = datetime.now(timezone.utc).isoformat()
    sido_code = sgg_code[:2]
    items = []
    page = 1
    while True:
        params = {
            "key": key,
            "sidoCode": sido_code,
            "sggCode": sgg_code,
            "pageCnt": PAGE_SIZE,
            "currentPage": page,
        }
        resp = session.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "SUCCESS":
            print(f"  [{sgg_code}] 오류 응답: {payload}", file=sys.stderr)
            break
        rows = payload.get("kinderInfo", [])
        for row in rows:
            row["_sidoCode"] = sido_code
            row["_sggCode"] = sgg_code
            items.append(map_item(row, sido_name, district_name, now))
        if len(rows) < PAGE_SIZE:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return items


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-url", default="https://ichapterwise.com/ingest-batch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--codes-file", default=str(SGG_CODES_FILE))
    args = parser.parse_args()

    key = os.environ.get("CHILD_SCHOOL_INFO_KEY")
    if not key:
        sys.exit("CHILD_SCHOOL_INFO_KEY 환경변수가 필요합니다")

    sgg_list = json.loads(Path(args.codes_file).read_text(encoding="utf-8"))
    session = requests.Session()

    buffer = []
    total = 0

    def flush():
        nonlocal buffer, total
        if not buffer or args.dry_run:
            buffer = []
            return
        payload = [{"item_type": "EducationFacilityItem", "data": d} for d in buffer]
        r = session.post(args.export_url, json=payload, timeout=30)
        r.raise_for_status()
        total += len(buffer)
        buffer = []

    for entry in sgg_list:
        sgg_code = entry["sggCode"]
        full_name = entry["name"]
        parts = full_name.split(" ", 1)
        sido_name = parts[0]
        district_name = parts[1] if len(parts) > 1 else ""

        try:
            items = fetch_region(session, key, sgg_code, sido_name, district_name)
        except requests.RequestException as exc:
            print(f"  [{sgg_code}] 요청 실패: {exc}", file=sys.stderr)
            continue

        print(f"{full_name} ({sgg_code}): {len(items)}건")
        buffer.extend(items)
        if len(buffer) >= BATCH_SIZE:
            flush()
        time.sleep(REQUEST_DELAY)

    flush()
    print(f"완료: 총 {total}건 적재 (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
