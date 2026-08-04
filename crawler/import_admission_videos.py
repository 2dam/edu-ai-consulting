"""수집한 입시 영상 JSON을 API의 전용 테이블에 일괄 적재한다."""

import argparse
import json
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="입시 영상 JSON API 적재")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--file", default="admission-youtube.json")
    args = parser.parse_args()

    source = Path(args.file)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("영상 JSON의 최상위 값은 배열이어야 합니다.")

    endpoint = f"{args.api_url.rstrip('/')}/videos/ingest-batch"
    response = requests.post(endpoint, json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    print(
        f"완료: 입력 {result['total']}건, 고유 {result['unique']}건, "
        f"중복 {result['duplicates']}건, 생성 {result['created']}건, 갱신 {result['updated']}건"
    )


if __name__ == "__main__":
    main()
