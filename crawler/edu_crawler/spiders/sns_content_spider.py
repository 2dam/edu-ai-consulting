"""
SNS 콘텐츠 수집 스파이더 — 2단계 파이프라인의 수집 담당.

aliens_eye_runner.py(1단계)가 발견한 학원 공식 SNS 계정 URL을 받아
공개 게시물의 제목·본문·해시태그를 수집한다.

지원 플랫폼 (공개 범위에서만 수집):
  - Naver 블로그: blog.naver.com/<id>
  - YouTube 채널: youtube.com/@<id> 또는 youtube.com/c/<id>
  - Instagram 공개 프로필: instagram.com/<id>  (메타태그 기반, 로그인 불필요 범위)

실행 예:
  scrapy crawl sns_content \
    -a academy_name="대치메가스터디" \
    -a sns_urls="https://blog.naver.com/megastudy,https://www.youtube.com/@megastudy" \
    -a region="강남"

또는 discover_and_crawl.py 를 통해 자동 실행됨.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy
from scrapling import Selector

from edu_crawler.items import SnsPostItem

_NAVER_POST_URL_RE = re.compile(r"blog\.naver\.com/([^/]+)/(\d+)")
_HASHTAG_RE = re.compile(r"#([\w가-힣]+)")


def _detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "naver" in host:
        return "naverblog"
    if "youtube" in host:
        return "youtube"
    if "instagram" in host:
        return "instagram"
    if "facebook" in host:
        return "facebook"
    if "tiktok" in host:
        return "tiktok"
    return "unknown"


class SnsContentSpider(scrapy.Spider):
    name = "sns_content"

    custom_settings = {
        # SNS 사이트는 빠른 요청을 차단할 수 있으므로 보수적으로 설정
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def __init__(self, academy_name=None, sns_urls=None, region="강남", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not sns_urls:
            raise ValueError("usage: -a sns_urls=<url1>,<url2>,...")
        self.academy_name = academy_name or "unknown"
        self.region = region
        self.sns_urls = [u.strip() for u in sns_urls.split(",") if u.strip()]

    def start_requests(self):
        for url in self.sns_urls:
            platform = _detect_platform(url)
            yield scrapy.Request(
                url,
                callback=self._dispatch,
                cb_kwargs={"platform": platform, "account_url": url},
                meta={"dont_redirect": False},
            )

    def _dispatch(self, response, platform, account_url):
        if platform == "naverblog":
            yield from self._parse_naver_blog(response, account_url)
        elif platform == "youtube":
            yield from self._parse_youtube(response, account_url)
        elif platform == "instagram":
            yield from self._parse_instagram(response, account_url)
        else:
            yield from self._parse_generic(response, platform, account_url)

    # ── Naver 블로그: 목록 페이지 → 개별 포스트 ─────────────────────────────
    def _parse_naver_blog(self, response, account_url):
        page = Selector(response.text, url=response.url)

        # 목록에서 개별 포스트 링크 수집 (여러 블로그 테마 CSS 순서대로 시도)
        post_links = (
            page.css("a.item .item-subject::attr(href)").getall()
            or page.css(".list_type2 .title::attr(href)").getall()
            or page.css("a[href*='/PostView']::attr(href)").getall()
            or page.css("a[class*='post']::attr(href)").getall()
        )

        for href in post_links[:20]:  # 최신 20개 포스트만
            yield response.follow(
                href,
                callback=self._parse_naver_post,
                cb_kwargs={"account_url": account_url},
            )

    def _parse_naver_post(self, response, account_url):
        page = Selector(response.text, url=response.url)

        title = (
            page.css(".se-title-text::text").get()
            or page.css(".pcol1::text").get()
            or page.css("title::text").get()
            or ""
        ).strip()

        body_parts = page.css(".se-main-container ::text, .post-view ::text").getall()
        body = " ".join(p.strip() for p in body_parts if p.strip())

        tags = list({m for m in _HASHTAG_RE.findall(body)})

        # 교육 관련 키워드가 없는 포스트는 스킵
        if not self._is_education_relevant(title + " " + body):
            return

        item = SnsPostItem()
        item["source_url"] = response.url
        item["platform"] = "naverblog"
        item["academy_name"] = self.academy_name
        item["region"] = self.region
        item["post_title"] = title
        item["post_body"] = body[:2000]
        item["published_at"] = page.css(".se_publishDate::text, .date::text").get(default="")
        item["hashtags"] = tags
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        yield item

    # ── YouTube: 채널 about/community 페이지 (공개 메타 정보만) ──────────────
    def _parse_youtube(self, response, account_url):
        page = Selector(response.text, url=response.url)

        title = page.css('meta[name="title"]::attr(content)').get(default="")
        description = page.css('meta[name="description"]::attr(content)').get(default="")
        tags = list({m for m in _HASHTAG_RE.findall(description)})

        if not (title or description):
            return

        item = SnsPostItem()
        item["source_url"] = response.url
        item["platform"] = "youtube"
        item["academy_name"] = self.academy_name
        item["region"] = self.region
        item["post_title"] = title
        item["post_body"] = description[:2000]
        item["published_at"] = ""
        item["hashtags"] = tags
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        yield item

        # 채널의 영상 목록 페이지로 이동 (공개 /videos 탭)
        videos_url = account_url.rstrip("/") + "/videos"
        yield response.follow(
            videos_url,
            callback=self._parse_youtube_videos,
            cb_kwargs={"account_url": account_url},
        )

    def _parse_youtube_videos(self, response, account_url):
        page = Selector(response.text, url=response.url)
        # YouTube 영상 제목은 OGP/JSON-LD에서 추출
        for script in page.css('script[type="application/ld+json"]::text').getall():
            try:
                import json
                data = json.loads(script)
                items_data = data if isinstance(data, list) else [data]
                for d in items_data:
                    name = d.get("name", "")
                    desc = d.get("description", "")
                    if not self._is_education_relevant(name + " " + desc):
                        continue
                    item = SnsPostItem()
                    item["source_url"] = d.get("url", response.url)
                    item["platform"] = "youtube"
                    item["academy_name"] = self.academy_name
                    item["region"] = self.region
                    item["post_title"] = name
                    item["post_body"] = desc[:2000]
                    item["published_at"] = d.get("uploadDate", "")
                    item["hashtags"] = list({m for m in _HASHTAG_RE.findall(desc)})
                    item["crawled_at"] = datetime.now(timezone.utc).isoformat()
                    yield item
            except Exception:
                pass

    # ── Instagram: OGP 메타태그 기반 (공개 프로필 범위만) ──────────────────
    def _parse_instagram(self, response, account_url):
        page = Selector(response.text, url=response.url)

        title = page.css('meta[property="og:title"]::attr(content)').get(default="")
        description = page.css('meta[property="og:description"]::attr(content)').get(default="")
        tags = list({m for m in _HASHTAG_RE.findall(description)})

        if not self._is_education_relevant(title + " " + description):
            return

        item = SnsPostItem()
        item["source_url"] = response.url
        item["platform"] = "instagram"
        item["academy_name"] = self.academy_name
        item["region"] = self.region
        item["post_title"] = title
        item["post_body"] = description[:2000]
        item["published_at"] = ""
        item["hashtags"] = tags
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        yield item

    # ── 범용 폴백 ────────────────────────────────────────────────────────────
    def _parse_generic(self, response, platform, account_url):
        page = Selector(response.text, url=response.url)
        title = page.css('meta[property="og:title"]::attr(content), title::text').get(default="")
        description = page.css('meta[property="og:description"]::attr(content), meta[name="description"]::attr(content)').get(default="")

        if not self._is_education_relevant(title + " " + description):
            return

        item = SnsPostItem()
        item["source_url"] = response.url
        item["platform"] = platform
        item["academy_name"] = self.academy_name
        item["region"] = self.region
        item["post_title"] = title.strip()
        item["post_body"] = description.strip()[:2000]
        item["published_at"] = ""
        item["hashtags"] = list({m for m in _HASHTAG_RE.findall(description)})
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        yield item

    # ── 교육 관련성 필터 ─────────────────────────────────────────────────────
    _EDU_KEYWORDS = {
        "입시", "수능", "내신", "학원", "강의", "커리큘럼", "합격",
        "수학", "영어", "과학", "국어", "사회", "수업", "성적", "대학",
        "모의고사", "논술", "면접", "특강", "반편성", "학습",
    }

    def _is_education_relevant(self, text: str) -> bool:
        return any(kw in text for kw in self._EDU_KEYWORDS)
