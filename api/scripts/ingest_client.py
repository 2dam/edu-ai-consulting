"""
ingest_client.py — /ingest-batch 호출 래퍼

수집 스크립트(collect_*.py)에서 import 해서 쓰거나, 단독으로도 사용.

환경변수:
  INGEST_BASE_URL  기본값 http://127.0.0.1:8000 (로컬). 운영은 https://ichapterwise.com
  CONTENT_INGEST_API_KEY  /ingest-batch 인증 키 (필수)

사용:
  from ingest_client import push_batch
  push_batch([{"item_type": "...", "data": {...}}, ...])
"""
from __future__ import annotations

import os
import sys

import requests

BASE_URL = os.getenv("INGEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("CONTENT_INGEST_API_KEY", "")


def push_batch(payloads: list[dict], base_url: str = BASE_URL, api_key: str = API_KEY) -> dict:
    if not api_key:
        raise RuntimeError("CONTENT_INGEST_API_KEY 가 필요합니다.")
    url = f"{base_url}/ingest-batch"
    resp = requests.post(
        url,
        json=payloads,
        headers={"X-Ingest-Key": api_key, "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # stdin 에서 JSON 배열(or JSONL) 읽어 밀어넣기
    import json

    raw = sys.stdin.read().strip()
    if not raw:
        print("stdin 에 payload 를 넣으세요", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if isinstance(data, dict):
        data = [data]
    out = push_batch(data)
    print(json.dumps(out, ensure_ascii=False))
