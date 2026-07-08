"""YouTube Data API v3 검색 연동 — 실시간 교육 동영상 패널용.

listType=search 같은 비공식 임베드 트릭은 YouTube가 자주 차단해서, 정식 Data API로
검색한 뒤 실제 videoId를 얻어 표준 embed URL(/embed/{videoId})을 쓴다.

API 키는 https://console.cloud.google.com 에서 "YouTube Data API v3"를 활성화하고
발급받는다 (무료 할당량: 하루 10,000 유닛, 검색 1회당 100유닛 — 약 하루 100회).
"""
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
# 검색 할당량이 적어(하루 약 100회, 검색 1회=100유닛) 캐시를 길게 유지한다.
# 패널 탭이 여러 개라 10분 캐시로는 하루 할당량을 금방 넘길 수 있어 4시간으로 늘림
# (탭 5개 * 하루 6회 = 30회/일 수준으로 유지).
_CACHE_TTL_SECONDS = 4 * 60 * 60
_cache: dict[str, tuple[float, dict | None]] = {}


def search_video(query: str) -> dict | None:
    """검색어에 맞는 최신 영상 1건을 찾아 {video_id, title, channel} 을 반환한다.

    YOUTUBE_API_KEY 미설정, API 오류, 검색 결과 없음 등은 모두 None으로 처리한다.
    """
    # 일부 호스팅 환경변수 UI에 붙는 공백/개행문자 방어.
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key or not query:
        return None

    if len(api_key) not in (0, 39):
        logger.warning(
            "YOUTUBE_API_KEY 길이가 예상(39자)과 다름: %d자 (%s...%s)",
            len(api_key), api_key[:4], api_key[-4:],
        )

    cached = _cache.get(query)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = {
        "key": api_key,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": 5,
        "order": "date",
        "relevanceLanguage": "ko",
        "safeSearch": "strict",
        "videoEmbeddable": "true",
        "videoSyndicated": "true",
    }
    try:
        res = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=8)
        res.raise_for_status()
        items = res.json().get("items", [])
    except requests.HTTPError as exc:
        logger.error("YouTube 검색 실패 (status=%s): %s", exc.response.status_code, exc.response.text[:300])
        return None
    except requests.RequestException as exc:
        logger.error("YouTube 검색 요청 실패: %s", exc)
        return None
    except ValueError:
        logger.error("YouTube 응답이 JSON이 아님: %s", res.text[:300])
        return None

    if not items:
        logger.info("YouTube 검색 결과 없음: %s", query)
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
