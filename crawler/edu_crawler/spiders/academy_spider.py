"""
민간 학원 홈페이지에서 공개된 커리큘럼 정보를 수집하는 스파이더.

광주대성학원(kjdaesung.com) 실측 확인 결과: 과정별 상세 내용은 HTML 텍스트가 아니라
페이지에 pdf.js로 렌더링되는 PDF 파일(`/school2/files/*.pdf`)에 들어있다. 그래서
이 스파이더는 (1) 메뉴에서 과정명 + 상세페이지 링크를 모으고, (2) 상세페이지 안의
PDF 경로를 찾아 다운로드한 뒤, (3) pdfplumber로 텍스트를 추출해 description으로 쓴다.

robots.txt 점검 결과 (2026-06-26): kjdaesung.com은 User-agent: * 규칙이 없고
Yeti(네이버)만 명시적으로 Allow — 일반 크롤러에 대한 차단 규칙이 없어 허용으로 판단.

실행 예:
  scrapy crawl academy -a start_url="https://www.kjdaesung.com/school2/" \
    -a academy_name="광주대성학원" -a region="광주"

대상 사이트마다 구조가 다르므로, 새 학원을 추가할 때는 NAV_LINK_SELECTOR /
PDF_URL_PATTERN을 그 사이트에 맞게 조정해야 한다.
"""
import re
from datetime import datetime, timezone
from io import BytesIO

import pdfplumber
import scrapy

from edu_crawler.items import CurriculumItem

PDF_URL_RE = re.compile(r"""['"](/[^'"]+\.pdf)['"]""")


class AcademySpider(scrapy.Spider):
    name = "academy"

    def __init__(self, start_url=None, academy_name=None, region=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<학원 홈페이지 메인 URL>")
        self.start_urls = [start_url]
        self.academy_name = academy_name or "unknown"
        self.region = region or "unknown"

    def parse(self, response):
        seen = set()
        for link in response.css("ul.dropdown-menu a.dropdown-item"):
            title = link.css("::text").get(default="").strip()
            href = link.attrib.get("href", "")
            if not title or not href or href in seen:
                continue
            seen.add(href)
            yield response.follow(
                href,
                callback=self.parse_course_page,
                cb_kwargs={"course_title": title},
            )

    def parse_course_page(self, response, course_title):
        match = PDF_URL_RE.search(response.text)
        if not match:
            return
        pdf_url = response.urljoin(match.group(1))
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
