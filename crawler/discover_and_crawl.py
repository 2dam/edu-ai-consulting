"""
1단계(Aliens Eye SNS 탐색) → 2단계(Scrapy 콘텐츠 수집) 자동 연결 실행 스크립트.
선택적으로 3단계(nodriver 비탐지 브라우저 크롤링)를 수행한다.

수집 전략 (학원 홈페이지):
  1차: 일반 Scrapy HTTP 스파이더
  2차 폴백: nodriver 비탐지 브라우저 (Cloudflare 등 안티봇 사이트 대응)

사용법:
    # 전체 gangnam_targets.json 대상 실행
    python discover_and_crawl.py

    # 특정 학원만
    python discover_and_crawl.py --academy "대치메가스터디학원"

    # 탐색만 (수집 스킵)
    python discover_and_crawl.py --discover-only

    # 수집만 (이전 탐색 결과 재사용)
    python discover_and_crawl.py --crawl-only --results-file discovered_accounts.json

    # nodriver 비탐지 크롤러로 홈페이지 수집
    python discover_and_crawl.py --stealth

    # nodriver로 SNS 공식 계정 수집
    python discover_and_crawl.py --stealth-sns
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discover_and_crawl")

TARGETS_FILE = Path(__file__).parent / "gangnam_targets.json"
RESULTS_FILE = Path(__file__).parent / "discovered_accounts.json"
API_URL = "http://localhost:8000"


def load_targets() -> list[dict]:
    return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))


def step1_discover(targets: list[dict]) -> list[dict]:
    """1단계: Aliens Eye로 SNS 계정 탐색."""
    from edu_crawler.snsdiscovery.aliens_eye_runner import discover_sns_accounts

    all_accounts: list[dict] = []
    for target in targets:
        name = target["academy_name"]
        region = target.get("region", "강남")
        logger.info("=== [1단계] %s 탐색 시작 ===", name)
        accounts = discover_sns_accounts(name, region=region)

        for acc in accounts:
            record = {
                "platform": acc.platform,
                "url": acc.url,
                "username": acc.username,
                "academy_name": acc.academy_name,
                "region": acc.region,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            }
            all_accounts.append(record)
            _ingest_sns_account(record)

    RESULTS_FILE.write_text(
        json.dumps(all_accounts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[1단계 완료] %d개 SNS 계정 발견 → %s", len(all_accounts), RESULTS_FILE)
    return all_accounts


def _ingest_sns_account(record: dict) -> None:
    """발견된 SNS 계정을 FastAPI /ingest 에 적재."""
    payload = {
        "item_type": "SnsAccountItem",
        "data": {**record, "source_url": record["url"]},
    }
    try:
        resp = requests.post(f"{API_URL}/ingest", json=payload, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("API ingest 실패 (계속 진행): %s", e)


def step2_crawl(accounts: list[dict]) -> None:
    """2단계: 발견된 SNS URL을 학원별로 묶어 sns_content_spider 실행."""
    # 학원별로 URL 그룹화
    by_academy: dict[str, dict] = {}
    for acc in accounts:
        key = acc["academy_name"]
        if key not in by_academy:
            by_academy[key] = {"region": acc["region"], "urls": []}
        by_academy[key]["urls"].append(acc["url"])

    for academy_name, info in by_academy.items():
        urls = ",".join(info["urls"])
        logger.info("=== [2단계] %s 콘텐츠 수집 시작 (%d개 URL) ===",
                    academy_name, len(info["urls"]))
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", "sns_content",
            "-a", f"academy_name={academy_name}",
            "-a", f"sns_urls={urls}",
            "-a", f"region={info['region']}",
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            logger.warning("[2단계] %s 수집 중 오류 발생 (returncode=%d)",
                           academy_name, result.returncode)

    logger.info("[2단계 완료]")


def step3_stealth_homepage(targets: list[dict], output_file: Path | None = None) -> None:
    """3단계: nodriver 비탐지 브라우저로 학원 홈페이지 직접 수집."""
    import asyncio
    from edu_crawler.stealth_crawler import crawl_stealth

    all_items: list[dict] = []
    for target in targets:
        name = target["academy_name"]
        url = target.get("website", "")
        region = target.get("region", "강남")
        if not url:
            logger.warning("[3단계] website URL 없음: %s — 스킵", name)
            continue
        logger.info("=== [3단계-홈페이지] %s ===", name)
        try:
            items = asyncio.run(crawl_stealth(url, name, region))
            for item in items:
                _ingest_item(item, "CurriculumItem")
            all_items.extend(items)
            logger.info("  → %d개 과정 수집", len(items))
        except Exception as exc:
            logger.error("[3단계] %s 수집 실패: %s", name, exc)

    if output_file:
        output_file.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[3단계 완료] %d개 저장 → %s", len(all_items), output_file)
    else:
        logger.info("[3단계 완료] %d개 수집", len(all_items))


def step3_stealth_sns(targets: list[dict], output_file: Path | None = None) -> None:
    """3단계(SNS): nodriver로 gangnam_targets.json 의 공식 SNS 계정을 직접 수집."""
    import asyncio
    from edu_crawler.stealth_crawler import crawl_sns_stealth

    all_items: list[dict] = []
    for target in targets:
        name = target["academy_name"]
        region = target.get("region", "강남")
        sns_map = target.get("sns", {})
        for platform, url in sns_map.items():
            if not url:
                continue
            logger.info("=== [3단계-SNS] %s / %s ===", name, platform)
            try:
                items = asyncio.run(crawl_sns_stealth(url, name, region, platform))
                for item in items:
                    _ingest_item(item, "SnsPostItem")
                all_items.extend(items)
                logger.info("  → %d개 게시물 수집", len(items))
            except Exception as exc:
                logger.error("[3단계-SNS] %s/%s 실패: %s", name, platform, exc)

    if output_file:
        output_file.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("[3단계-SNS 완료] %d개 → %s", len(all_items), output_file)
    else:
        logger.info("[3단계-SNS 완료] %d개 수집", len(all_items))


def _ingest_item(item: dict, item_type: str) -> None:
    payload = {"item_type": item_type, "data": {**item, "source_url": item.get("source_url", "")}}
    try:
        resp = requests.post(f"{API_URL}/ingest", json=payload, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("API ingest 실패 (계속 진행): %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aliens Eye 탐색 → Scrapy/nodriver 수집 파이프라인")
    parser.add_argument("--academy", default=None, help="특정 학원명만 처리")
    parser.add_argument("--discover-only", action="store_true", help="탐색(1단계)만 수행")
    parser.add_argument("--crawl-only", action="store_true", help="수집(2단계)만 수행")
    parser.add_argument("--stealth", action="store_true", help="nodriver로 학원 홈페이지 수집 (3단계)")
    parser.add_argument("--stealth-sns", action="store_true", help="nodriver로 공식 SNS 수집 (3단계)")
    parser.add_argument("--results-file", default=str(RESULTS_FILE), help="discovered_accounts.json 경로")
    parser.add_argument("--output", default=None, help="수집 결과 저장 파일 경로")
    args = parser.parse_args()

    targets = load_targets()
    if args.academy:
        targets = [t for t in targets if args.academy in t["academy_name"]]
        if not targets:
            logger.error("'%s' 에 해당하는 학원이 gangnam_targets.json 에 없습니다.", args.academy)
            sys.exit(1)

    output_file = Path(args.output) if args.output else None

    # 3단계 단독 실행
    if args.stealth:
        step3_stealth_homepage(targets, output_file)
        return
    if args.stealth_sns:
        step3_stealth_sns(targets, output_file)
        return

    if args.crawl_only:
        results_path = Path(args.results_file)
        if not results_path.exists():
            logger.error("results-file 이 없습니다: %s", results_path)
            sys.exit(1)
        accounts = json.loads(results_path.read_text(encoding="utf-8"))
        step2_crawl(accounts)
        return

    accounts = step1_discover(targets)

    if not args.discover_only and accounts:
        step2_crawl(accounts)
    elif not accounts:
        logger.warning("발견된 SNS 계정이 없어 2단계를 건너뜁니다.")


if __name__ == "__main__":
    main()
