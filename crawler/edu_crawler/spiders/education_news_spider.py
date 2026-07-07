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

CSS 셀렉터는 사이트마다 다르므로 예시 placeholder다 — 실제 대상 사이트 HTML 구조에
맞춰 조정해야 한다 (public_data_spider.py와 동일한 상황).

실행 예:
  scrapy crawl education_news -a start_url="<교육 뉴스 목록 URL>" -a category="정책" -a region="광주"
"""
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy

from edu_crawler.items import EducationNewsItem

# 도메인 -> 표시용 매체명. 반드시 위 절차대로 robots.txt를 직접 확인한 뒤에만 추가할 것.
# (아직 실측 검증된 도메인이 없어 비어 있음 — admission_result_spider.py의 대학 화이트리스트와
#  달리 이번 스파이더는 실제 대상 매체가 정해지기 전까지 빈 상태로 둔다.)
ALLOWED_SOURCES: dict[str, str] = {}


class EducationNewsSpider(scrapy.Spider):
    name = "education_news"

    # 크롤러 전용 신규 라우트로 전송 — api/app/routers/news.py의 POST /news/ingest.
    # 기존 ApiExportPipeline은 전혀 수정하지 않고 스파이더 단위로만 EXPORT_API_URL을 오버라이드한다.
    custom_settings = {"EXPORT_API_URL": "http://localhost:8000/news/ingest"}

    def __init__(self, start_url=None, category=None, region=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<교육 뉴스 목록 URL> [-a category=정책|입시|트렌드] [-a region=지역명]")

        domain = urlparse(start_url).netloc
        if domain not in ALLOWED_SOURCES:
            raise ValueError(
                f"'{domain}'은(는) ALLOWED_SOURCES 화이트리스트에 없습니다. "
                f"먼저 robots.txt와 로그인 필요 여부를 직접 확인하고 등재하세요. "
                f"허용된 출처: {sorted(ALLOWED_SOURCES) or '(없음 — 아직 등재된 출처 없음)'}"
            )

        self.start_urls = [start_url]
        self.source_name = ALLOWED_SOURCES[domain]
        self.category = category or ""
        self.region = region or ""

    def parse(self, response):
        now = datetime.now(timezone.utc).isoformat()

        for row in response.css(".news-list li, .board-list tr, article.news-item"):
            href = row.css("a::attr(href)").get(default="")
            title = row.css("a::text, .title::text").get(default="").strip()
            if not title or not href:
                continue

            yield response.follow(
                href,
                callback=self.parse_article,
                cb_kwargs={
                    "title": title,
                    "list_thumbnail": row.css("img::attr(src)").get(default=""),
                    "list_published_at": row.css(".date::text, time::text").get(default="").strip(),
                    "crawled_at": now,
                },
            )

    def parse_article(self, response, title, list_thumbnail, list_published_at, crawled_at):
        body_text = "\n".join(
            t.strip()
            for t in response.css("article p::text, .article-body p::text, .view-content ::text").getall()
            if t.strip()
        )
        thumbnail_url = response.urljoin(list_thumbnail) if list_thumbnail else response.css(
            "meta[property='og:image']::attr(content)"
        ).get(default="")
        tags = [
            t.strip()
            for t in response.css(".tag-list a::text, .keyword::text").getall()
            if t.strip()
        ]

        item = EducationNewsItem()
        item["title"] = title
        item["url"] = response.url
        item["source"] = self.source_name
        item["published_at"] = list_published_at
        item["category"] = self.category
        item["body_text"] = body_text
        item["thumbnail_url"] = thumbnail_url
        item["region"] = self.region
        item["tags"] = tags
        item["crawled_at"] = crawled_at
        if item["body_text"]:
            yield item
