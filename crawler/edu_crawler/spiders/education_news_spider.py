"""
공개 교육 뉴스 매체(교육부/시도교육청 보도자료, 공개 교육 전문지 등)에서 기사 목록/본문을
수집해 AI 교육 뉴스 커뮤니티 모듈(api의 NewsPost)로 보내는 스파이더.

절대 하지 않는 것 (계획서 6.1항 + 커뮤니티 모듈 안전 요구사항):
  - 로그인이 필요한 커뮤니티/사설 카페/맘카페 크롤링
  - 개인정보(작성자 실명, 연락처 등)가 포함된 게시물 수집
  - robots.txt 미확인 도메인 크롤링 (settings.py의 ROBOTSTXT_OBEY=True는 항상 유지, 끄지 않음)

admission_result_spider.py의 ROBOTSTXT_WHITELIST 패턴을 그대로 따라, 이 스파이더도
ALLOWED_SOURCES 화이트리스트에 등재된 도메인에서만 동작한다. 새 출처를 추가하려면:
  1. 해당 도메인 robots.txt를 직접 확인해 일반 User-agent가 차단되지 않는지 검증
  2. 로그인 없이 누구나 열람 가능한 공개 뉴스/보도자료 페이지인지 확인
  3. 확인 날짜와 함께 ALLOWED_SOURCES에 등재
검증 전 도메인으로 실행하면 즉시 에러를 내고 크롤링을 시작하지 않는다
(robots.txt 미들웨어에만 맡기지 않고 코드 차원에서도 한 번 더 막는다).

실행 예:
  scrapy crawl education_news \
    -a start_url="https://www.moe.go.kr/boardCnts/listRenew.do?boardID=294&m=020402&s=moe" \
    -a category="정책"
"""
from datetime import datetime, timezone
import re
from urllib.parse import parse_qs, urlencode, urlparse

import scrapy

from edu_crawler.items import EducationNewsItem

SOURCE_CONFIGS = {
    "www.moe.go.kr": {
        "name": "교육부",
        "list_path": "/boardCnts/listRenew.do",
        "required_query": {"boardID": "294"},
        "row_selector": "table tbody tr",
        "link_selector": "td.title a[onclick*='goView']",
        "date_selector": "td:nth-child(4)::text",
        "body_selector": "#txt .synapTextWrap ::text",
        "license_selector": "#txt .attachment ::text",
        "license_marker": "공공누리",
        "license_tag": "공공누리 출처표시",
        "checked_at": "2026-08-03",
    }
}

# 기존 코드와 운영 점검 도구에서 간단히 허용 도메인을 확인할 수 있도록 유지한다.
ALLOWED_SOURCES: dict[str, str] = {
    domain: config["name"] for domain, config in SOURCE_CONFIGS.items()
}


def _is_allowed_list_url(url: str, config: dict) -> bool:
    parsed = urlparse(url)
    if parsed.path != config["list_path"]:
        return False
    query = parse_qs(parsed.query)
    return all(query.get(key) == [value] for key, value in config["required_query"].items())


def _education_ministry_article_url(onclick: str) -> str:
    match = re.search(r"goView\(\s*'294'\s*,\s*'(\d+)'", onclick or "")
    if not match:
        return ""
    query = urlencode(
        {
            "boardID": "294",
            "boardSeq": match.group(1),
            "lev": "0",
            "m": "020402",
            "opType": "N",
            "s": "moe",
            "statusYN": "W",
        }
    )
    return f"https://www.moe.go.kr/boardCnts/viewRenew.do?{query}"


class EducationNewsSpider(scrapy.Spider):
    name = "education_news"

    # 크롤러 전용 신규 라우트로 전송 — api/app/routers/news.py의 POST /news/ingest.
    # 기존 ApiExportPipeline은 전혀 수정하지 않고 스파이더 단위로만 EXPORT_API_URL을 오버라이드한다.
    custom_settings = {
        "EXPORT_API_URL": "http://localhost:8000/news/ingest",
        # 공식 보도자료 수집에서는 브라우저 대체 요청이나 차단 우회를 사용하지 않는다.
        "DOWNLOADER_MIDDLEWARES": {
            "edu_crawler.middlewares.ScraplingFallbackMiddleware": None,
        },
    }

    def __init__(self, start_url=None, category=None, region=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<교육 뉴스 목록 URL> [-a category=정책|입시|트렌드] [-a region=지역명]")

        domain = (urlparse(start_url).hostname or "").lower()
        if domain not in SOURCE_CONFIGS:
            raise ValueError(
                f"'{domain}'은(는) ALLOWED_SOURCES 화이트리스트에 없습니다. "
                f"먼저 robots.txt와 로그인 필요 여부를 직접 확인하고 등재하세요. "
                f"허용된 출처: {sorted(ALLOWED_SOURCES) or '(없음 — 아직 등재된 출처 없음)'}"
            )

        self.source_config = SOURCE_CONFIGS[domain]
        if not _is_allowed_list_url(start_url, self.source_config):
            raise ValueError("허용 도메인이더라도 검증된 교육부 보도자료 목록 URL만 사용할 수 있습니다.")

        self.start_urls = [start_url]
        self.source_name = self.source_config["name"]
        self.category = category or ""
        self.region = region or ""

    def parse(self, response):
        now = datetime.now(timezone.utc).isoformat()

        for row in response.css(self.source_config["row_selector"]):
            link = row.css(self.source_config["link_selector"])
            onclick = link.attrib.get("onclick", "")
            article_url = _education_ministry_article_url(onclick)
            title = " ".join(link.css("::text").getall()).strip()
            if not title or not article_url:
                continue

            yield scrapy.Request(
                article_url,
                callback=self.parse_article,
                cb_kwargs={
                    "title": title,
                    "list_published_at": row.css(self.source_config["date_selector"]).get(default="").strip(),
                    "crawled_at": now,
                },
            )

    def parse_article(self, response, title, list_published_at, crawled_at):
        license_text = " ".join(response.css(self.source_config["license_selector"]).getall())
        if self.source_config["license_marker"] not in license_text:
            self.logger.warning("공공누리 이용조건을 확인할 수 없어 제외합니다: %s", response.url)
            return

        body_text = "\n".join(
            t.strip()
            for t in response.css(self.source_config["body_selector"]).getall()
            if t.strip()
        )
        thumbnail_url = response.css("meta[property='og:image']::attr(content)").get(default="")

        item = EducationNewsItem()
        item["title"] = title
        item["url"] = response.url
        item["source"] = self.source_name
        item["published_at"] = list_published_at
        item["category"] = self.category
        item["body_text"] = body_text
        item["thumbnail_url"] = thumbnail_url
        item["region"] = self.region
        item["tags"] = [self.source_config["license_tag"]]
        item["crawled_at"] = crawled_at
        if item["body_text"]:
            yield item
