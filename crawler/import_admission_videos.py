"""?섏쭛???낆떆 ?곸긽 JSON??API???꾩슜 ?뚯씠釉붿뿉 ?쇨큵 ?곸옱?쒕떎."""

import argparse
import json
import os
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="?낆떆 ?곸긽 JSON API ?곸옱")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--file", default="admission-youtube.json")
    args = parser.parse_args()

    source = Path(args.file)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("?곸긽 JSON??理쒖긽??媛믪? 諛곗뿴?댁뼱???⑸땲??")

    endpoint = f"{args.api_url.rstrip('/')}/videos/ingest-batch"
    ingest_key = os.getenv("VIDEO_INGEST_API_KEY", "").strip()
    if not ingest_key:
        raise RuntimeError("VIDEO_INGEST_API_KEY environment variable is required")
    response = requests.post(
        endpoint,
        json=payload,
        headers={"X-Ingest-Key": ingest_key},
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    print(
        f"?꾨즺: ?낅젰 {result['total']}嫄? 怨좎쑀 {result['unique']}嫄? "
        f"以묐났 {result['duplicates']}嫄? ?앹꽦 {result['created']}嫄? 媛깆떊 {result['updated']}嫄?
    )


if __name__ == "__main__":
    main()

