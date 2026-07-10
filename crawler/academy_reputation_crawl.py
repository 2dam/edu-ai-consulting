"""
학원 평판 인텔리전스(api/app/routers/reputation.py)에 등록된 학원을 대상으로 SNS 공개
게시물을 수집하는 로컬 CLI 브릿지.

discover_and_crawl.py의 1단계(SNS 계정 탐색, aliens_eye)/2단계(sns_content_spider 콘텐츠
수집) 파이프라인을 그대로 재사용하되, 대상을 gangnam_targets.json 대신 우리 Academy DB의
등록 정보(GET /reputation/academies/{id}/crawl-targets)에서 가져온다.

scrapy는 이 프로젝트의 배포 서비스(render.yaml)에 포함돼 있지 않다 — 크롤은 항상
운영자가 로컬에서 이 스크립트를 실행해 수행하고, 수집 결과는 discover_and_crawl.py와 동일하게
ApiExportPipeline이 백엔드 /ingest-batch로 보낸다. 그 후 대시보드에서 "SNS 언급 동기화"를
누르면 API가 감성점수화해서 반영한다(사이트 크롤링 자체를 API 서비스에서 하지 않는다).

사용법:
    python academy_reputation_crawl.py --academy-id 1
    python academy_reputation_crawl.py --academy-id 1 --discover  # 등록된 SNS 소스가 없을 때 aliens_eye로 먼저 탐색
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("academy_reputation_crawl")

API_URL = "http://localhost:8000"
ADMIN_USER_ID = "1"  # api/app/auth.py의 ADMIN_USER_IDS와 일치해야 함


def fetch_crawl_targets(academy_id: int) -> dict:
    res = requests.get(
        f"{API_URL}/reputation/academies/{academy_id}/crawl-targets",
        headers={"X-User-Id": ADMIN_USER_ID},
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def discover_more_urls(academy_name: str, region: str) -> list[str]:
    """등록된 SNS 소스가 없을 때 aliens_eye로 공식 계정을 탐색한다(--discover 옵션)."""
    from edu_crawler.snsdiscovery.aliens_eye_runner import discover_sns_accounts

    accounts = discover_sns_accounts(academy_name, region=region)
    return [acc.url for acc in accounts]


def run_sns_content_crawl(academy_name: str, region: str, sns_urls: list[str]) -> None:
    urls = ",".join(sns_urls)
    logger.info("=== %s 콘텐츠 수집 시작 (%d개 URL) ===", academy_name, len(sns_urls))
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", "sns_content",
        "-a", f"academy_name={academy_name}",
        "-a", f"sns_urls={urls}",
        "-a", f"region={region or '미상'}",
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.warning("수집 중 오류 발생 (returncode=%d)", result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="학원 평판 모듈에 등록된 학원의 SNS 공개 게시물 수집")
    parser.add_argument("--academy-id", type=int, required=True, help="reputation 모듈의 Academy.id")
    parser.add_argument("--discover", action="store_true", help="등록된 SNS 소스가 없을 때 aliens_eye로 먼저 탐색")
    args = parser.parse_args()

    try:
        targets = fetch_crawl_targets(args.academy_id)
    except requests.RequestException as exc:
        logger.error("crawl-targets 조회 실패 — API 서버(%s)가 실행 중인지 확인하세요: %s", API_URL, exc)
        sys.exit(1)

    academy_name = targets["academy_name"]
    region = targets.get("region") or "미상"
    sns_urls = list(targets.get("sns_urls", []))

    if not sns_urls:
        if not args.discover:
            logger.warning(
                "'%s'에 등록된 SNS 소스 URL이 없습니다. 대시보드의 '공개 소스 URL'에 블로그/유튜브/"
                "인스타그램 링크를 등록하거나, --discover 옵션으로 자동 탐색을 시도하세요.",
                academy_name,
            )
            return
        logger.info("등록된 SNS 소스가 없어 aliens_eye로 탐색합니다...")
        sns_urls = discover_more_urls(academy_name, region)
        if not sns_urls:
            logger.warning("'%s'의 공식 SNS 계정을 찾지 못했습니다.", academy_name)
            return

    run_sns_content_crawl(academy_name, region, sns_urls)
    logger.info("완료 — 대시보드에서 'SNS 언급 동기화'를 눌러 반영하세요.")


if __name__ == "__main__":
    main()
