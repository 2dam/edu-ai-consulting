"""
민간 학원 홈페이지에서 공개된 커리큘럼 정보를 수집하는 스파이더.

ROBOTSTXT_OBEY=True (settings.py) 가 켜져 있어 robots.txt 가 막은 경로는
Scrapy 가 자동으로 건너뜀. 그래도 크롤링 전에 대상 사이트의 이용약관을
직접 확인할 것 (계획서 6.1항).

실행 예:
  scrapy crawl academy -a start_url="https://example-academy.co.kr/curriculum" -a academy_name="OO학원" -a region="강남"

대상 사이트마다 HTML 구조가 다르므로 parse() 안의 CSS 셀렉터는
실제 타겟 사이트에 맞게 수정해야 함 (지금은 일반적인 패턴 예시).
"""
from datetime import datetime, timezone

import scrapy

from edu_crawler.items import CurriculumItem


class AcademySpider(scrapy.Spider):
    name = "academy"

    def __init__(self, start_url=None, academy_name=None, region=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<커리큘럼 페이지 URL>")
        self.start_urls = [start_url]
        self.academy_name = academy_name or "unknown"
        self.region = region or "unknown"

    def parse(self, response):
        # 예시 셀렉터 — 실제 학원 사이트 구조에 맞게 교체 필요.
        for course in response.css(".course-list .course-item, .curriculum-item"):
            item = CurriculumItem()
            item["source_url"] = response.url
            item["academy_name"] = self.academy_name
            item["region"] = self.region
            item["subject"] = course.css(".subject::text, .course-subject::text").get(default="").strip()
            item["course_title"] = course.css(".title::text, .course-title::text").get(default="").strip()
            item["description"] = " ".join(course.css("p::text").getall()).strip()
            item["crawled_at"] = datetime.now(timezone.utc).isoformat()
            if item["course_title"]:
                yield item
