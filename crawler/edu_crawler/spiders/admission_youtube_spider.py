"""공식 YouTube Data API v3 기반 입시 관련 공개 영상 수집기.

HTML·댓글·자막을 스크래핑하지 않고 검색 및 영상 메타데이터 API만 사용한다.
검색 API는 호출당 할당량 비용이 크므로 기본값은 검색어별 25건, 최대 2페이지다.

실행 예:
  scrapy crawl admission_youtube -O admission-youtube.json
  scrapy crawl admission_youtube -a queries="2027 대입,수시 학생부종합,정시 수능" -a max_results=50
"""

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import scrapy

from edu_crawler.items import AdmissionVideoItem


SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
DEFAULT_QUERIES = (
    "대입 입시",
    "수시 학생부종합",
    "정시 수능",
    "대학 입학전형",
)


class AdmissionYoutubeSpider(scrapy.Spider):
    name = "admission_youtube"
    allowed_domains = ["www.googleapis.com"]
    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # 웹 크롤링이 아닌 인증된 공식 API 호출
        "DOWNLOAD_DELAY": 0.2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def __init__(
        self,
        queries=None,
        max_results=25,
        max_pages=1,
        published_days=365,
        order="date",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY 환경변수가 필요합니다.")

        self.queries = tuple(
            q.strip() for q in (queries.split(",") if queries else DEFAULT_QUERIES) if q.strip()
        )
        self.max_results = min(max(int(max_results), 1), 50)
        self.max_pages = min(max(int(max_pages), 1), 5)
        self.published_days = max(int(published_days), 1)
        if order not in {"date", "relevance", "viewCount"}:
            raise ValueError("order는 date, relevance, viewCount 중 하나여야 합니다.")
        self.order = order

    def start_requests(self):
        published_after = (
            datetime.now(timezone.utc) - timedelta(days=self.published_days)
        ).isoformat().replace("+00:00", "Z")
        for query in self.queries:
            yield self._search_request(query, published_after, page=1)

    def _search_request(self, query, published_after, page, page_token=None):
        params = {
            "key": self.api_key,
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": self.max_results,
            "order": self.order,
            "publishedAfter": published_after,
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "safeSearch": "strict",
            "videoEmbeddable": "true",
            "videoSyndicated": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        return scrapy.Request(
            f"{SEARCH_URL}?{urlencode(params)}",
            callback=self.parse_search,
            cb_kwargs={"query": query, "published_after": published_after, "page": page},
        )

    def parse_search(self, response, query, published_after, page):
        payload = response.json()
        if payload.get("error"):
            reason = payload["error"].get("message", "YouTube API error")
            raise ValueError(f"YouTube 검색 실패: {reason}")

        search_items = payload.get("items", [])
        ids = [item.get("id", {}).get("videoId") for item in search_items]
        ids = [video_id for video_id in ids if video_id]
        if ids:
            params = {
                "key": self.api_key,
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(ids),
            }
            yield scrapy.Request(
                f"{VIDEOS_URL}?{urlencode(params)}",
                callback=self.parse_videos,
                cb_kwargs={"query": query},
            )

        next_token = payload.get("nextPageToken")
        if next_token and page < self.max_pages:
            yield self._search_request(query, published_after, page + 1, next_token)

    def parse_videos(self, response, query):
        payload = response.json()
        now = datetime.now(timezone.utc).isoformat()
        for video in payload.get("items", []):
            if video.get("status", {}).get("privacyStatus") != "public":
                continue
            video_id = video.get("id", "")
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}

            item = AdmissionVideoItem()
            item["source_url"] = f"https://www.youtube.com/watch?v={video_id}"
            item["platform"] = "youtube"
            item["video_id"] = video_id
            item["title"] = snippet.get("title", "")
            item["description"] = snippet.get("description", "")
            item["channel_id"] = snippet.get("channelId", "")
            item["channel_title"] = snippet.get("channelTitle", "")
            item["published_at"] = snippet.get("publishedAt", "")
            item["thumbnail_url"] = thumbnail.get("url", "")
            item["duration"] = video.get("contentDetails", {}).get("duration", "")
            item["view_count"] = int(statistics.get("viewCount", 0) or 0)
            item["like_count"] = int(statistics.get("likeCount", 0) or 0)
            item["comment_count"] = int(statistics.get("commentCount", 0) or 0)
            item["search_query"] = query
            item["crawled_at"] = now
            if video_id and item["title"]:
                yield item
