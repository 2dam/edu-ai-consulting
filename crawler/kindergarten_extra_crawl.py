"""유치원알리미 부가 공시항목(안전점검, 급식, 교직원 등) 전국 크롤.

kindergarten_crawl.py(기본현황/basicInfo2)와 같은 인증·페이징 구조를 쓰지만
오퍼레이션마다 응답 필드가 달라 EducationFacilityItem에 억지로 끼워맞추지 않고,
kindercode로 나중에 조인 가능하도록 오퍼레이션별 item_type(Raw 그대로)으로 적재한다.

사용법:
    CHILD_SCHOOL_INFO_KEY=<인증키> python kindergarten_extra_crawl.py safety
    CHILD_SCHOOL_INFO_KEY=<인증키> python kindergarten_extra_crawl.py meal --dry-run
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

BASE_URL = "https://e-childschoolinfo.moe.go.kr/api/notice"
SGG_CODES_FILE = Path(__file__).parent / "sgg_codes.json"
PAGE_SIZE = 100
REQUEST_DELAY = 1.0
BATCH_SIZE = 50

# 오퍼레이션명 -> (엔드포인트 파일명, item_type)
OPERATIONS = {
    "safety": ("safetyEdu.do", "KindergartenSafetyItem"),
    "meal": ("schoolMeal.do", "KindergartenMealItem"),
    "teachers": ("teachersInfo.do", "KindergartenTeacherItem"),
    "building": ("building.do", "KindergartenBuildingItem"),
    "classarea": ("classArea.do", "KindergartenClassAreaItem"),
    "lessonday": ("lessonDay.do", "KindergartenLessonDayItem"),
    "bus": ("schoolBus.do", "KindergartenBusItem"),
    "yearofwork": ("yearOfWork.do", "KindergartenYearOfWorkItem"),
    "hygiene": ("environmentHygiene.do", "KindergartenHygieneItem"),
    "deduction": ("deductionSociety.do", "KindergartenDeductionItem"),
}


def fetch_region(session, api_url, key, sgg_code, sido_name, district_name):
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
        resp = session.get(api_url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "SUCCESS":
            print(f"  [{sgg_code}] 오류 응답: {payload}", file=sys.stderr)
            break
        rows = payload.get("kinderInfo", [])
        for row in rows:
            data = dict(row)
            data["region"] = sido_name
            data["district"] = district_name
            data["source_url"] = f"{api_url}?sidoCode={sido_code}&sggCode={sgg_code}"
            data["crawled_at"] = now
            items.append(data)
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
    parser.add_argument("operation", choices=sorted(OPERATIONS))
    parser.add_argument("--export-url", default="https://ichapterwise.com/ingest-batch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--codes-file", default=str(SGG_CODES_FILE))
    args = parser.parse_args()

    key = os.environ.get("CHILD_SCHOOL_INFO_KEY")
    if not key:
        sys.exit("CHILD_SCHOOL_INFO_KEY 환경변수가 필요합니다")

    endpoint_file, item_type = OPERATIONS[args.operation]
    api_url = f"{BASE_URL}/{endpoint_file}"

    sgg_list = json.loads(Path(args.codes_file).read_text(encoding="utf-8"))
    session = requests.Session()

    buffer = []
    total = 0
    request_count = 0

    def flush():
        nonlocal buffer, total
        if not buffer or args.dry_run:
            buffer = []
            return
        payload = [{"item_type": item_type, "data": d} for d in buffer]
        for attempt in range(3):
            try:
                r = session.post(args.export_url, json=payload, timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == 2:
                    print(f"  배치 전송 실패 (3회 재시도 후 포기, {len(buffer)}건 유실): {exc}", file=sys.stderr)
                    buffer = []
                    return
                print(f"  배치 전송 실패, 재시도 {attempt + 1}/3: {exc}", file=sys.stderr)
                time.sleep(5)
        total += len(buffer)
        buffer = []

    for entry in sgg_list:
        sgg_code = entry["sggCode"]
        full_name = entry["name"]
        parts = full_name.split(" ", 1)
        sido_name = parts[0]
        district_name = parts[1] if len(parts) > 1 else ""

        try:
            items = fetch_region(session, api_url, key, sgg_code, sido_name, district_name)
        except requests.RequestException as exc:
            print(f"  [{sgg_code}] 요청 실패: {exc}", file=sys.stderr)
            continue

        print(f"{full_name} ({sgg_code}): {len(items)}건")
        buffer.extend(items)
        if len(buffer) >= BATCH_SIZE:
            flush()
        time.sleep(REQUEST_DELAY)

    flush()
    print(f"완료 [{args.operation}/{item_type}]: 총 {total}건 적재 (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
