"""
민간 학원 홈페이지에서 공개된 커리큘럼 정보를 수집하는 스파이더.

[Scrapling 통합 사항]
- Scrapling Adaptor를 파서로 사용해 다중 CSS 패턴을 순서대로 시도한다.
  한 패턴이 실패해도 다음 패턴을 자동으로 시도하므로 사이트 구조 변경에 강하다.
- -a use_playwright=1 옵션으로 ScraplingFallbackMiddleware가 PlaywrightFetcher를
  사용하게 강제한다 (Cloudflare·JS 렌더링 필요 사이트용).
- 403/503 응답은 ScraplingFallbackMiddleware가 자동으로 재시도한다 (settings.py 참고).

광주대성학원(kjdaesung.com) 실측 확인 결과: 과정별 상세 내용은 HTML 텍스트가 아니라
페이지에 pdf.js로 렌더링되는 PDF 파일(`/school2/files/*.pdf`)에 들어있다.

robots.txt 점검 결과 (2026-06-26): kjdaesung.com은 User-agent: * 규칙이 없고
Yeti(네이버)만 명시적으로 Allow — 일반 크롤러에 대한 차단 규칙이 없어 허용으로 판단.

실행 예 (일반):
  scrapy crawl academy -a start_url="https://www.kjdaesung.com/school2/" \\
    -a academy_name="광주대성학원" -a region="광주"

실행 예 (Cloudflare 차단 사이트):
  scrapy crawl academy -a start_url="https://www.blocked-academy.com/" \\
    -a academy_name="예시학원" -a region="서울" -a use_playwright=1

실행 예 (구조를 모르는 완전 신규 사이트 → browser_use_spider 권장):
  python -m edu_crawler.spiders.browser_use_spider \\
    --url "https://www.unknown-academy.co.kr" --academy "신규학원" --region "부산"
"""
import re
from datetime import datetime, timezone
from io import BytesIO

import pdfplumber
import scrapy
from scrapling import Selector

from edu_crawler.items import CurriculumItem

PDF_URL_RE = re.compile(r"""['"](/[^'"]+\.pdf)['"]""")

# 한국 학원 사이트에서 흔히 쓰이는 메뉴 링크 셀렉터 (우선순위 순).
# 새 학원 추가 시 해당 사이트의 패턴을 맨 앞에 추가하면 된다.
_NAV_SELECTORS = [
    "ul.dropdown-menu a.dropdown-item",  # Bootstrap 기반 (kjdaesung.com 등)
    "#gnb a[href]",                       # 국산 CMS 상단 메뉴
    "#lnb a[href]",                       # 국산 CMS 좌측 메뉴
    ".gnb a[href]", ".lnb a[href]",
    "nav a[href]", ".nav a[href]",
    ".menu a[href]", ".sidebar a[href]",
    "ul.menu li a[href]",
    "ul.nav li a[href]",
]


class AcademySpider(scrapy.Spider):
    name = "academy"

    def __init__(
        self,
        start_url=None,
        academy_name=None,
        region=None,
        use_playwright=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<학원 홈페이지 메인 URL>")
        self.start_urls = [start_url]
        self.academy_name = academy_name or "unknown"
        self.region = region or "unknown"
        # "-a use_playwright=1" or "-a use_playwright=true" 모두 허용
        self._use_playwright = bool(
            use_playwright and str(use_playwright).lower() not in ("0", "false", "no")
        )

    def start_requests(self):
        meta = {}
        if self._use_playwright:
            meta["use_scrapling_playwright"] = True
        for url in self.start_urls:
            yield scrapy.Request(url, meta=meta)

    def parse(self, response):
        # Scrapling Selector로 파싱 — 다중 셀렉터 패턴 순서대로 시도
        page = Selector(response.text, url=response.url)
        seen = set()

        links = []
        for selector in _NAV_SELECTORS:
            links = page.css(selector)
            if links:
                self.logger.debug("매칭된 셀렉터: %s (%d개 링크)", selector, len(links))
                break

        if not links:
            self.logger.warning(
                "메뉴 링크를 찾지 못함 (%s). "
                "이 사이트는 JS 렌더링이 필요하거나 구조가 다를 수 있습니다. "
                "-a use_playwright=1 옵션을 시도하거나 browser_use_spider를 사용하세요.",
                response.url,
            )
            return

        for link in links:
            title = (link.css("::text").get(default="") or "").strip()
            href = (link.css("::attr(href)").get(default="") or "").strip()
            if not title or not href or href in seen:
                continue
            seen.add(href)

            meta = {}
            if self._use_playwright:
                meta["use_scrapling_playwright"] = True

            yield response.follow(
                href,
                callback=self.parse_course_page,
                cb_kwargs={"course_title": title},
                meta=meta,
            )

    def parse_course_page(self, response, course_title):
        match = PDF_URL_RE.search(response.text)
        if not match:
            return
        pdf_url = response.urljoin(match.group(1))
        # PDF는 바이너리 응답 — Scrapling 미들웨어가 개입하지 않도록 표시
        yield scrapy.Request(
            pdf_url,
            callback=self.parse_pdf,
            cb_kwargs={"course_title": course_title, "page_url": response.url},
        )

    def parse_pdf(self, response, course_title, page_url):
        text_parts = []
        with pdfplumber.open(BytesIO(response.body)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        item = CurriculumItem()
        item["source_url"] = page_url
        item["academy_name"] = self.academy_name
        item["region"] = self.region
        item["subject"] = ""
        item["course_title"] = course_title
        item["description"] = "\n".join(text_parts).strip()
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        if item["description"]:
            yield item
