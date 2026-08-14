"""
collect_admissions.py — 대학 입학처 공시 입결 데이터 수집 → AdmissionResultItem ingest

출처: 대학입학정보포털(www.adiga.kr 등) 또는 각 대학 입학처 공시 '입결결과'
공시 자료는 대학 x 학과 x 전형 x 연도 별 '충원인원/지원자/합격자/등록자/평균등급' 등을 포함.

⚠️ 실제 구조:
  - 대학입학정보포털은 로그인/세션 기반이라 단순 GET 크롤링이 안 될 수 있음.
  - 각 대학 입학처가 공시하는 '입결결과 표'는 학교마다 HTML/PDF 형태라 파싱 난이도 상이.
  이 스크립트는:
    1. --csv 로 이미 수집된 공시 표(CSV)를 읽는 경로 (가장 현실적)
    2. 또는 --sample-json 으로 단일 대학 JSON 샘플을 변환하는 경로
  를 제공. 실제 포털 자동 크롤링은 별도 크롤러(rate-limit/세션 처리)로 확장 필요.

매핑(IngestPayload):
  item_type = "AdmissionResultItem"
  data = { university, department, admission_type, year, region,
           recruited, applied, admitted, enrolled, avg_grade, source_url }
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

ITEM_TYPE = "AdmissionResultItem"


def log(*a: Any) -> None:
    print("[collect_admissions]", *a, file=sys.stderr, flush=True)


def _get(row: dict, *cands: str, default: Any = None) -> Any:
    for c in cands:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return default


def to_payload(row: dict, source_url: str = "") -> dict:
    return {
        "item_type": ITEM_TYPE,
        "data": {
            "source_url": _get(row, "source_url", default=source_url),
            "facility_type": "university",
            "region": _get(row, "region", "지역", default=""),
            "university": _get(row, "university", "대학", "univ_nm", default=""),
            "department": _get(row, "department", "학과", "dept_nm", default=""),
            "admission_type": _get(row, "admission_type", "전형", default=""),
            "year": _get(row, "year", "연도", default=""),
            "recruited": _get(row, "recruited", "충원", "recruit_nmpr", default=0),
            "applied": _get(row, "applied", "지원", "applcnt_nmpr", default=0),
            "admitted": _get(row, "admitted", "합격", "admit_nmpr", default=0),
            "enrolled": _get(row, "enrolled", "등록", "enroll_nmpr", default=0),
            "avg_grade": _get(row, "avg_grade", "평균등급", "avg_grd", default=None),
            "collected_at": _get(row, "collected_at", default=time.strftime("%Y-%m-%d")),
        },
    }


def from_csv(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            yield to_payload(row)


def from_json(path: str, source_url: str = "") -> Iterable[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data if isinstance(data, list) else data.get("rows", [data])
    for r in rows:
        yield to_payload(r, source_url)


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="수집된 입결 공시 CSV 경로")
    src.add_argument("--sample-json", help="단일 대학 입결 JSON 샘플 경로")
    ap.add_argument("--source-url", default="", help="출처 URL (샘플용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from ingest_client import push_batch  # type: ignore
        pusher = push_batch
    except Exception:  # noqa: BLE001
        pusher = None

    gen = from_csv(args.csv) if args.csv else from_json(args.sample_json, args.source_url)
    total = 0
    buf: list[dict] = []
    BATCH = 100
    for p in gen:
        total += 1
        if args.dry_run:
            print(json.dumps(p, ensure_ascii=False))
            continue
        buf.append(p)
        if len(buf) >= BATCH:
            if pusher:
                pusher(buf)
            else:
                print(json.dumps(buf, ensure_ascii=False))
            buf = []
    if buf and not args.dry_run:
        if pusher:
            pusher(buf)
        else:
            print(json.dumps(buf, ensure_ascii=False))
    log(f"완료 — 총 {total}건" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
