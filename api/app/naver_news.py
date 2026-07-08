"""네이버 뉴스 검색 오픈API 연동 — 실시간 교육 뉴스 패널용.

발급: https://developers.naver.com 에서 애플리케이션 등록 후 "검색" API 추가.
무료 할당량 하루 25,000회. 저작권/AI 학습 제한 문구 없음(연합뉴스 RSS와 달리 검색
결과의 제목·요약·링크만 제공하는 공식 오픈API).
"""
import logging
import os
import re
import time
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)

NAVER_NEWS_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"

_CACHE_TTL_SECONDS = 30 * 60
_cache: dict[str, tuple[float, list[dict]]] = {}

_TAG_RE = re.compile(r"<[^>]+>")

_CATEGORY_KEYWORDS = [
    ("수능", "수능"),
    ("정시", "대입"),
    ("수시", "대입"),
    ("대입", "대입"),
    ("학원", "학원"),
    ("교육격차", "정책"),
    ("교육부", "정책"),
    ("사교육", "정책"),
]


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).replace("&quot;", '"').replace("&amp;", "&").strip()


def _guess_category(title: str) -> str:
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in title:
            return category
    return "교육"


def _guess_source(originallink: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)", originallink)
    return m.group(1) if m else "네이버뉴스"


def search_news(query: str, display: int = 20) -> list[dict]:
    """검색어에 맞는 최신 뉴스 목록을 반환한다. 키 미설정/오류 시 빈 리스트."""
    client_id = os.environ.get("NAVER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret or not query:
        return []

    cached = _cache.get(query)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": display, "sort": "date"}
    try:
        res = requests.get(NAVER_NEWS_SEARCH_URL, headers=headers, params=params, timeout=8)
        res.raise_for_status()
        items = res.json().get("items", [])
    except requests.HTTPError as exc:
        logger.error("네이버 뉴스 검색 실패 (status=%s): %s", exc.response.status_code, exc.response.text[:300])
        return []
    except requests.RequestException as exc:
        logger.error("네이버 뉴스 검색 요청 실패: %s", exc)
        return []
    except ValueError:
        logger.error("네이버 뉴스 응답이 JSON이 아님: %s", res.text[:300])
        return []

    results = []
    for item in items:
        title = _strip_html(item.get("title", ""))
        originallink = item.get("originallink") or item.get("link", "")
        pub_date_raw = item.get("pubDate", "")
        try:
            pub_date_iso = parsedate_to_datetime(pub_date_raw).isoformat()
        except (TypeError, ValueError):
            pub_date_iso = None
        if not title or not originallink:
            continue
        results.append(
            {
                "title": title,
                "source": _guess_source(originallink),
                "url": originallink,
                "category": _guess_category(title),
                "pub_date": pub_date_iso,
            }
        )

    _cache[query] = (time.time(), results)
    return results
