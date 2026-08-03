"""커리어넷 공식 Open API의 대학 학과 목록 수집기.

실행:
  scrapy crawl careernet_university_majors -O career-majors.json
"""

import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import scrapy

from edu_crawler.items import CareerMajorItem


API_URL = "https://www.career.go.kr/cnet/openapi/getOpenApi"


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def extract_major_page(payload: dict) -> tuple[list[dict], int]:
    """커리어넷 JSON 응답에서 목록과 전체 건수를 정규화한다."""
    root = payload.get("dataSearch", payload)
    contents = root.get("content", []) if isinstance(root, dict) else []
    rows = [row for row in _as_list(contents) if isinstance(row, dict)]
    raw_total = root.get("totalCount", len(rows)) if isinstance(root, dict) else len(rows)
    try:
        total = int(str(raw_total).replace(",", ""))
    except (TypeError, ValueError):
        total = len(rows)
    return rows, total


class CareerNetUniversityMajorSpider(scrapy.Spider):
    name = "careernet_university_majors"
    allowed_domains = ["www.career.go.kr"]
    page_size = 100
    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOADER_MIDDLEWARES": {
            "edu_crawler.middlewares.ScraplingFallbackMiddleware": None,
            "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": None,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("CAREERNET_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("CAREERNET_API_KEY 환경변수가 필요합니다.")

    def start_requests(self):
        yield self._request_page(1)

    def _request_page(self, page: int):
        query = urlencode(
            {
                "apiKey": self.api_key,
                "svcType": "api",
                "svcCode": "MAJOR",
                "contentType": "json",
                "gubun": "univ_list",
                "thisPage": page,
                "perPage": self.page_size,
            }
        )
        return scrapy.Request(
            f"{API_URL}?{query}",
            method="GET",
            cb_kwargs={"page": page},
            callback=self.parse,
        )

    def parse(self, response, page: int):
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("커리어넷 API가 JSON이 아닌 응답을 반환했습니다.") from exc

        if isinstance(payload, dict) and payload.get("error"):
            raise ValueError(f"커리어넷 API 오류: {payload['error']}")

        rows, total = extract_major_page(payload)
        if not rows:
            self.logger.warning("커리어넷 학과 목록 %s페이지에 항목이 없습니다.", page)
            return

        crawled_at = datetime.now(timezone.utc).isoformat()
        for row in rows:
            major_code = str(row.get("majorSeq", "")).strip()
            major_name = str(row.get("mClass", "")).strip()
            department = str(row.get("facilName", "")).strip()
            if not (major_code or major_name or department):
                continue

            item = CareerMajorItem()
            item["source_url"] = "https://www.career.go.kr/cnet/front/openapi/openApiMajorCenter.do"
            item["major_code"] = major_code
            item["major_name"] = major_name
            item["category"] = str(row.get("lClass", "")).strip()
            item["department"] = department
            item["crawled_at"] = crawled_at
            yield item

        if page * self.page_size < total:
            yield self._request_page(page + 1)
