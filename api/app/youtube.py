"""YouTube Data API v3 검색 연동 — 실시간 교육 동영상 패널용.

listType=search 같은 비공식 임베드 트릭은 YouTube가 자주 차단해서, 정식 Data API로
검색한 뒤 실제 videoId를 얻어 표준 embed URL(/embed/{videoId})을 쓴다.

API 키는 https://console.cloud.google.com 에서 "YouTube Data API v3"를 활성화하고
발급받는다 (무료 할당량: 하루 10,000 유닛, 검색 1회당 100유닛 — 약 하루 100회).
"""
import os
import time

import requests

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
# 검색 할당량이 적어(하루 약 100회) 캐시를 길게 유지한다.
_CACHE_TTL_SECONDS = 600
_cache: dict[str, tuple[float, dict | None]] = {}


def search_video(query: str) -> dict | None:
    """검색어에 맞는 최신 영상 1건을 찾아 {video_id, title, channel} 을 반환한다.

    YOUTUBE_API_KEY 미설정, API 오류, 검색 결과 없음 등은 모두 None으로 처리한다.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key or not query:
        return None

    cached = _cache.get(query)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = {
        "key": api_key,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": 1,
        "order": "date",
        "relevanceLanguage": "ko",
        "safeSearch": "strict",
    }
    try:
        res = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=8)
        res.raise_for_status()
        items = res.json().get("items", [])
    except (requests.RequestException, ValueError):
        return None

    if not items:
        result = None
    else:
        snippet = items[0].get("snippet", {})
        result = {
            "video_id": items[0].get("id", {}).get("videoId", ""),
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
        }
        if not result["video_id"]:
            result = None

    _cache[query] = (time.time(), result)
    return result
