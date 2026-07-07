"""
Aliens Eye CLI 래퍼 — 학원명에서 파생된 후보 username 목록을 840+ 플랫폼에서 검색해
공식 SNS 계정 URL을 반환한다.

사용 패턴:
    from edu_crawler.snsdiscovery.aliens_eye_runner import discover_sns_accounts
    results = discover_sns_accounts("대치메가스터디", region="강남")

역할: "존재 여부 탐색"만 수행 — 콘텐츠 수집은 sns_content_spider.py가 담당.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 교육 컨설팅에서 가치 있는 플랫폼만 필터링 — 한국 학원이 주로 활동하는 채널 기준.
# aliens_eye 는 840+ 플랫폼을 검색하지만 여기서는 유의미한 것만 추출한다.
TARGET_PLATFORMS = {
    "instagram",
    "youtube",
    "twitter",
    "naverblog",   # aliens_eye 결과에서 naver 계열로 표시될 수 있음
    "naver",
    "kakao",
    "facebook",
    "tiktok",
    "linkedin",
}

# 학원명 → 후보 username 변환 규칙.
# 실제 SNS 계정명은 예측 불가하므로 여러 변형을 시도해 커버리지를 높인다.
_CLEANUP_RE = re.compile(r"[\s\-_./·]+")
_STRIP_RE = re.compile(r"(학원|아카데미|학습관|입시|교육|원|영어|수학|과학)$")


def _candidate_usernames(academy_name: str) -> list[str]:
    """학원명에서 SNS 계정 후보 username 목록을 생성한다."""
    base = _CLEANUP_RE.sub("", academy_name).lower()
    stripped = _STRIP_RE.sub("", base)
    candidates = {base, stripped}
    if len(stripped) > 2:
        candidates.add(stripped + "_official")
        candidates.add(stripped + "_kr")
    return [c for c in candidates if c]


@dataclass
class SnsAccount:
    platform: str
    url: str
    username: str
    academy_name: str
    region: str
    source_username_tried: str


def _run_aliens_eye(username: str, timeout: int = 60) -> list[dict]:
    """aliens_eye CLI를 subprocess로 실행해 JSON 결과를 파싱한다."""
    cmd = [sys.executable, "-m", "aliens_eye", "check", username, "--output", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        logger.error("aliens_eye 가 설치되지 않았습니다. 'pip install aliens-eye' 를 실행하세요.")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("aliens_eye timeout for username=%s", username)
        return []

    output = proc.stdout.strip()
    if not output:
        logger.debug("aliens_eye: no output for username=%s", username)
        return []

    # JSON 블록만 추출 (rich 터미널 출력이 섞일 수 있음)
    json_match = re.search(r"\[.*\]", output, re.DOTALL)
    if not json_match:
        logger.debug("aliens_eye: JSON 파싱 실패 for username=%s, raw=%s", username, output[:200])
        return []

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("aliens_eye: JSON decode error for username=%s", username)
        return []


def discover_sns_accounts(
    academy_name: str,
    region: str = "강남",
    timeout_per_username: int = 60,
) -> list[SnsAccount]:
    """academy_name 에서 파생된 후보 username들을 aliens_eye로 검색해
    실제로 발견된 SNS 계정 목록을 반환한다."""
    found: list[SnsAccount] = []
    seen_urls: set[str] = set()

    for username in _candidate_usernames(academy_name):
        logger.info("[aliens_eye] 탐색 중: %s (학원=%s)", username, academy_name)
        raw_results = _run_aliens_eye(username, timeout=timeout_per_username)

        for entry in raw_results:
            platform = (entry.get("platform") or entry.get("site") or "").lower()
            url = entry.get("url") or entry.get("link") or ""
            status = (entry.get("status") or "").lower()

            # "found" 상태이고 관심 플랫폼인 경우만 수집
            if status != "found":
                continue
            if not any(t in platform for t in TARGET_PLATFORMS):
                continue
            if url in seen_urls:
                continue

            seen_urls.add(url)
            found.append(SnsAccount(
                platform=platform,
                url=url,
                username=username,
                academy_name=academy_name,
                region=region,
                source_username_tried=username,
            ))
            logger.info("  발견: %s → %s", platform, url)

    return found
