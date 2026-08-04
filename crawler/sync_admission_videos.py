
"""Collect recent admission videos and upsert them into the production API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests


def main() -> None:
    api_base_url = os.getenv("API_BASE_URL", "https://ichapterwise.com").rstrip("/")
    ingest_key = os.getenv("VIDEO_INGEST_API_KEY", "").strip()
    if not os.getenv("YOUTUBE_API_KEY", "").strip():
        raise RuntimeError("YOUTUBE_API_KEY environment variable is required")
    if not ingest_key:
        raise RuntimeError("VIDEO_INGEST_API_KEY environment variable is required")

    with tempfile.TemporaryDirectory(prefix="admission-videos-") as temp_dir:
        output = Path(temp_dir) / "videos.json"
        crawler_env = os.environ.copy()
        crawler_env["SCRAPY_SETTINGS_MODULE"] = "edu_crawler.settings_youtube"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "scrapy",
                "crawl",
                "admission_youtube",
                "-a",
                "published_days=7",
                "-a",
                "max_results=25",
                "-a",
                "max_pages=1",
                "-O",
                str(output),
            ],
            check=True,
            env=crawler_env,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))

    if not payload:
        print("No admission videos returned by YouTube; nothing to sync.")
        return

    response = requests.post(
        f"{api_base_url}/videos/ingest-batch",
        json=payload,
        headers={"X-Ingest-Key": ingest_key},
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    print(
        "Admission video sync complete: "
        f"total={result['total']} unique={result['unique']} "
        f"created={result['created']} updated={result['updated']}"
    )


if __name__ == "__main__":
    main()

