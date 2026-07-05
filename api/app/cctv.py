"""국가교통정보센터(ITS) 공공 CCTV Open API 연동.

도로·거리의 공공(교통/방범) 실시간 CCTV 스트림 URL을 지도에 표시하기 위한 프록시.
API 키는 https://openapi.its.go.kr 에서 무료로 발급받아 ITS_API_KEY 환경변수에 설정한다.

주의: 어린이집·유치원·학교 시설 "내부" CCTV는 영유아보육법 등에 따라 원아 보호자·
관할 지자체·수사기관 등으로 열람 권한이 엄격히 제한되어 있어 이 프로젝트에서 다루지
않는다. 여기서 연동하는 것은 오직 ITS가 공개하는 도로 구간 CCTV뿐이다.
"""
import os
import time

import requests

ITS_CCTV_URL = "https://openapi.its.go.kr:9443/cctvInfo"
_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, list[dict]]] = {}

# 전국 범위 기본값 (경도/위도)
KOREA_BBOX = {"min_x": 124.5, "min_y": 33.0, "max_x": 131.0, "max_y": 43.0}


def fetch_cctv(min_x: float, min_y: float, max_x: float, max_y: float, cctv_type: int = 1) -> list[dict]:
    """bbox(경도/위도) 내 공공 도로 CCTV 목록을 조회한다.

    cctv_type: 1=실시간 스트리밍(HLS 등), 2=정지 영상
    ITS_API_KEY 미설정 시 빈 목록을 반환한다 (프론트에서는 "키 미설정" 상태로 처리).
    """
    api_key = os.environ.get("ITS_API_KEY", "")
    if not api_key:
        return []

    cache_key = f"{min_x:.2f}:{min_y:.2f}:{max_x:.2f}:{max_y:.2f}:{cctv_type}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    params = {
        "apiKey": api_key,
        "type": "all",
        "cctvType": cctv_type,
        "minX": min_x,
        "maxX": max_x,
        "minY": min_y,
        "maxY": max_y,
        "getType": "json",
    }
    try:
        res = requests.get(ITS_CCTV_URL, params=params, timeout=8)
        res.raise_for_status()
        raw_items = res.json().get("response", {}).get("data", [])
    except (requests.RequestException, ValueError):
        return []

    result = [
        {
            "name": it.get("cctvname", ""),
            "lat": float(it.get("coordy") or 0),
            "lng": float(it.get("coordx") or 0),
            "stream_url": it.get("cctvurl", ""),
            "format": it.get("cctvformat", ""),
        }
        for it in raw_items
        if it.get("cctvurl")
    ]
    _cache[cache_key] = (time.time(), result)
    return result
