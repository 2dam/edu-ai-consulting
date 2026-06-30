"""
nodriver 기반 비탐지 브라우저 크롤러.

stealth-browser-mcp(github.com/vibheksoni/stealth-browser-mcp)의 핵심 엔진인
nodriver를 직접 사용해 Cloudflare·안티봇 보호가 걸린 사이트에서
학원 커리큘럼·SNS 공개 정보를 수집한다.

일반 Scrapy 스파이더로 접근이 막히는 경우의 폴백 크롤러.

실행 예:
    cd crawler
    python -m edu_crawler.stealth_crawler \\
        --url "https://www.megastudy.net" \\
        --academy "대치메가스터디학원" --region "서울 대치"

    # 여러 학원 일괄:
    python -m edu_crawler.stealth_crawler \\
        --targets-file gangnam_targets.json --region "서울 강남"

보안 원칙:
    - 공식 학원 사이트·공식 SNS 페이지만 대상으로 한다.
    - 개인(학부모·학생) 계정·게시물은 수집하지 않는다.
    - robots.txt 를 사전에 확인하고, Disallow 경로는 건너뛴다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests as _requests

logger = logging.getLogger(__name__)

# 교육 관련성 판단 키워드
_EDU_KEYWORDS = re.compile(
    r"입시|수능|내신|학원|강의|커리큘럼|합격|수학|영어|국어|과학|사탐|과탐|"
    r"모의고사|수시|정시|논술|면접|자소서|과정|반|클래스|수업|강좌",
    re.IGNORECASE,
)

# 수집 대상 정보 추출 패턴
_COURSE_SECTION_PATTERNS = [
    "수업", "강좌", "과정", "커리큘럼", "프로그램",
    "class", "course", "curriculum",
]


def _check_robots(base_url: str, target_path: str = "/") -> bool:
    """robots.txt 를 확인해 해당 경로 접근 허용 여부를 반환."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser(robots_url)
        rp.read()
        allowed = rp.can_fetch("*", base_url)
        if not allowed:
            logger.warning("robots.txt 차단: %s", base_url)
        return allowed
    except Exception as exc:
        logger.debug("robots.txt 확인 실패 (%s) — 접근 허용으로 처리", exc)
        return True


def _is_edu_relevant(text: str) -> bool:
    return bool(_EDU_KEYWORDS.search(text))


async def _extract_page_info(tab, url: str) -> dict:
    """탭에서 텍스트·링크·구조를 추출해 교육 정보 딕셔너리로 반환."""
    try:
        # 전체 텍스트
        text = await tab.evaluate("document.body.innerText")
        # 페이지 제목
        title = await tab.evaluate("document.title")
        # 주요 헤딩
        headings_js = """
        Array.from(document.querySelectorAll('h1,h2,h3'))
             .map(h => h.innerText.trim())
             .filter(t => t.length > 0)
             .slice(0, 30)
        """
        headings = await tab.evaluate(headings_js)
        # 내부 링크 (과정·수업 관련)
        links_js = """
        Array.from(document.querySelectorAll('a[href]'))
             .map(a => ({text: a.innerText.trim(), href: a.href}))
             .filter(l => l.text.length > 0 && l.href.startsWith('http'))
             .slice(0, 50)
        """
        links = await tab.evaluate(links_js)
    except Exception as exc:
        logger.warning("페이지 추출 실패 (%s): %s", url, exc)
        text, title, headings, links = "", "", [], []

    return {
        "url": url,
        "title": title or "",
        "text": (text or "")[:5000],  # 최대 5,000자
        "headings": headings or [],
        "links": links or [],
    }


def _parse_courses_from_text(text: str, headings: list[str], academy_name: str) -> list[dict]:
    """
    텍스트·헤딩에서 과정 정보를 휴리스틱으로 파싱.
    LLM 없이 동작하는 폴백 파서.
    """
    courses = []
    subject_map = {
        "수학": "수학", "영어": "영어", "국어": "국어", "과학": "과학",
        "사회": "사회", "물리": "과학", "화학": "과학", "생물": "과학",
        "지구과학": "과학", "한국사": "사회", "경제": "사회",
    }

    lines = [h.strip() for h in headings if h.strip() and _is_edu_relevant(h)]
    for line in lines:
        subject = next((v for k, v in subject_map.items() if k in line), "")
        courses.append({
            "course_title": line,
            "subject": subject,
            "description": "",
            "academy_name": academy_name,
        })

    # 헤딩 없으면 텍스트에서 패턴 검색
    if not courses:
        for match in re.finditer(r"([^\n]{5,40}(?:반|클래스|과정|강좌|수업)[^\n]{0,40})", text):
            title = match.group(1).strip()
            if _is_edu_relevant(title):
                subject = next((v for k, v in subject_map.items() if k in title), "")
                courses.append({
                    "course_title": title,
                    "subject": subject,
                    "description": "",
                    "academy_name": academy_name,
                })
    return courses[:20]  # 최대 20개


async def crawl_stealth(
    url: str,
    academy_name: str,
    region: str,
    headless: bool = True,
    wait_seconds: int = 3,
) -> list[dict]:
    """
    nodriver로 단일 URL을 크롤링해 커리큘럼 아이템 목록을 반환.

    robots.txt 차단 시 빈 리스트 반환.
    """
    import nodriver as uc  # noqa: PLC0415 — 설치 여부 체크를 런타임으로 미룸

    if not _check_robots(url):
        return []

    logger.info("[stealth] 브라우저 시작: %s", url)
    browser = await uc.start(headless=headless)
    try:
        tab = await browser.get(url)
        # 페이지 로드 대기 (Cloudflare 챌린지 통과 포함)
        await asyncio.sleep(wait_seconds)

        page_info = await _extract_page_info(tab, url)
        crawled_at = datetime.now(timezone.utc).isoformat()

        if not _is_edu_relevant(page_info["text"] + " ".join(page_info["headings"])):
            logger.info("[stealth] 교육 관련 콘텐츠 없음: %s", url)
            raw_items = []
        else:
            raw_items = _parse_courses_from_text(
                page_info["text"], page_info["headings"], academy_name
            )

        # 과정 링크 재방문 (최대 3개)
        sub_links = [
            l["href"] for l in page_info["links"]
            if _is_edu_relevant(l["text"]) and _check_robots(l["href"])
        ][:3]

        for sub_url in sub_links:
            logger.info("[stealth] 하위 페이지: %s", sub_url)
            try:
                sub_tab = await browser.get(sub_url)
                await asyncio.sleep(2)
                sub_info = await _extract_page_info(sub_tab, sub_url)
                raw_items.extend(
                    _parse_courses_from_text(sub_info["text"], sub_info["headings"], academy_name)
                )
                await sub_tab.close()
            except Exception as exc:
                logger.warning("[stealth] 하위 페이지 오류 (%s): %s", sub_url, exc)

        # 중복 제거
        seen, items = set(), []
        for item in raw_items:
            key = item["course_title"]
            if key not in seen:
                seen.add(key)
                items.append({
                    "source_url": url,
                    "academy_name": academy_name,
                    "region": region,
                    "subject": item.get("subject", ""),
                    "course_title": item["course_title"],
                    "description": item.get("description", ""),
                    "crawled_at": crawled_at,
                    "crawler": "stealth_nodriver",
                })

        logger.info("[stealth] 수집 완료: %d개 과정 (%s)", len(items), academy_name)
        return items

    finally:
        browser.stop()


async def crawl_sns_stealth(
    sns_url: str,
    academy_name: str,
    region: str,
    platform: str = "unknown",
    headless: bool = True,
) -> list[dict]:
    """
    SNS 공식 계정 페이지(Instagram·YouTube·네이버블로그 등)를
    nodriver로 렌더링해 공개 게시물 텍스트를 수집.

    개인 계정이 아닌 학원 공식 계정만 대상으로 한다.
    """
    import nodriver as uc

    if not _check_robots(sns_url):
        return []

    logger.info("[stealth-sns] %s 크롤링: %s", platform, sns_url)
    browser = await uc.start(headless=headless)
    try:
        tab = await browser.get(sns_url)
        await asyncio.sleep(4)  # SNS 특히 느리게 로드됨

        # 스크롤해서 더 많은 게시물 로드
        await tab.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        page_info = await _extract_page_info(tab, sns_url)
        crawled_at = datetime.now(timezone.utc).isoformat()

        if not _is_edu_relevant(page_info["text"]):
            logger.info("[stealth-sns] 교육 관련 없음: %s", sns_url)
            return []

        # 게시물 단위 분리 (단락 기준)
        paragraphs = [
            p.strip() for p in page_info["text"].split("\n\n")
            if len(p.strip()) > 20 and _is_edu_relevant(p)
        ][:10]

        return [
            {
                "source_url": sns_url,
                "platform": platform,
                "academy_name": academy_name,
                "region": region,
                "post_title": page_info["title"],
                "post_body": para,
                "published_at": None,
                "hashtags": re.findall(r"#\S+", para),
                "crawled_at": crawled_at,
                "crawler": "stealth_nodriver",
            }
            for para in paragraphs
        ]

    finally:
        browser.stop()


def _post_to_api(items: list[dict], item_type: str, api_url: str) -> None:
    for item in items:
        payload = {"item_type": item_type, "data": item}
        try:
            _requests.post(api_url, json=payload, timeout=5)
        except _requests.RequestException as exc:
            logger.warning("API 전송 실패: %s", exc)


async def _run_targets(targets: list[dict], region: str, api_url: str, no_api: bool, output: str | None) -> None:
    all_items: list[dict] = []
    for t in targets:
        url = t.get("url") or t.get("homepage_url", "")
        name = t.get("name") or t.get("academy_name", "")
        if not url or not name:
            logger.warning("url/name 없는 항목 스킵: %s", t)
            continue
        items = await crawl_stealth(url, name, region)
        all_items.extend(items)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        logger.info("저장: %s (%d개)", output, len(all_items))
    elif no_api:
        print(json.dumps(all_items, ensure_ascii=False, indent=2))

    if not no_api:
        _post_to_api(all_items, "CurriculumItem", api_url)
        logger.info("API 전송 완료: %d개", len(all_items))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    parser = argparse.ArgumentParser(description="nodriver 비탐지 브라우저 학원 크롤러")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--url", help="단일 학원 URL")
    grp.add_argument("--targets-file", help="학원 목록 JSON (gangnam_targets.json 형식)")
    parser.add_argument("--academy", help="학원 이름 (--url 사용 시 필수)")
    parser.add_argument("--region", default="서울 강남", help="지역 (기본: 서울 강남)")
    parser.add_argument("--api-url", default="http://localhost:8000/ingest")
    parser.add_argument("--output", default=None, help="JSON 파일 저장 경로")
    parser.add_argument("--no-api", action="store_true", help="API 전송 없이 stdout/파일만")
    parser.add_argument("--visible", action="store_true", help="브라우저 창 표시 (디버깅용)")
    parser.add_argument(
        "--sns-url", default=None,
        help="SNS 단독 크롤링 URL (--url과 함께 사용 가능, 결과는 SnsPostItem으로 전송)"
    )
    parser.add_argument("--sns-platform", default="unknown", help="SNS 플랫폼 이름")
    args = parser.parse_args()

    headless = not args.visible

    try:
        import nodriver  # noqa: F401
    except ImportError:
        print("오류: nodriver 미설치. 다음 명령으로 설치하세요:", file=sys.stderr)
        print("  pip install nodriver==0.47.0", file=sys.stderr)
        sys.exit(1)

    # SNS 단독 크롤링
    if args.sns_url:
        academy = args.academy or "unknown"
        items = asyncio.run(
            crawl_sns_stealth(args.sns_url, academy, args.region, args.sns_platform, headless)
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        elif args.no_api:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        if not args.no_api:
            _post_to_api(items, "SnsPostItem", args.api_url)
        return

    # 단일 URL
    if args.url:
        if not args.academy:
            parser.error("--url 사용 시 --academy 가 필요합니다.")
        items = asyncio.run(crawl_stealth(args.url, args.academy, args.region, headless))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        elif args.no_api:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        if not args.no_api:
            _post_to_api(items, "CurriculumItem", args.api_url)
        return

    # 다중 타겟
    with open(args.targets_file, encoding="utf-8") as f:
        targets = json.load(f)
    asyncio.run(_run_targets(targets, args.region, args.api_url, args.no_api, args.output))


if __name__ == "__main__":
    main()
