"""메가스터디 공개 커리큘럼 목록 전용 스파이더.

로그인, 수강신청, 결제, 강의 영상 및 교재 본문에는 접근하지 않는다. 실행할 때마다
robots.txt를 먼저 읽고 이 봇과 대상 URL이 명시적으로 허용되는 경우에만 공개 목록
한 페이지를 요청한다. robots.txt를 가져오지 못하면 fail-closed로 종료한다.

실행:
  scrapy crawl megastudy_curriculum -O megastudy.json
"""

import re
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser

import scrapy
from scrapy.exceptions import CloseSpider

from edu_crawler.items import CurriculumItem

ROBOTS_URL = "https://www.megastudy.net/robots.txt"
CURRICULUM_URL = "https://www.megastudy.net/teacher_v2/curriculum/main.asp"
BOT_NAME = "EduAIConsultingBot"
COURSE_ID_RE = re.compile(r"fncChrDetailView\(['\"]?(\d+)['\"]?\s*,\s*['\"]?(\d+)")
SUBJECTS = ("국어", "수학", "영어", "한국사", "사회", "과학", "논술", "제2외국어", "한문")


def extract_course_id(onclick: str) -> str | None:
    match = COURSE_ID_RE.search(onclick or "")
    return match.group(1) if match else None


def infer_subject(title: str) -> str:
    normalized = title.replace("사회탐구", "사회").replace("과학탐구", "과학")
    return next((subject for subject in SUBJECTS if subject in normalized), "")


class MegastudyCurriculumSpider(scrapy.Spider):
    name = "megastudy_curriculum"
    allowed_domains = ["www.megastudy.net"]

    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        # 이 사이트에는 403/503 우회 또는 브라우저 폴백을 사용하지 않는다.
        "DOWNLOADER_MIDDLEWARES": {
            "edu_crawler.middlewares.ScraplingFallbackMiddleware": None,
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            ROBOTS_URL,
            callback=self.parse_robots,
            errback=self.robots_failed,
            dont_filter=True,
            meta={"handle_httpstatus_all": True},
        )

    def parse_robots(self, response):
        if response.status != 200:
            raise CloseSpider(f"robots_unavailable_http_{response.status}")

        parser = RobotFileParser()
        parser.set_url(ROBOTS_URL)
        parser.parse(response.text.splitlines())
        if not parser.can_fetch(BOT_NAME, CURRICULUM_URL):
            raise CloseSpider("robots_disallowed")

        yield scrapy.Request(CURRICULUM_URL, callback=self.parse_curriculum)

    def robots_failed(self, failure):
        self.logger.error("robots.txt 확인 실패: %s", failure.getErrorMessage())
        raise CloseSpider("robots_unavailable")

    def parse_curriculum(self, response):
        links = response.css("a.lecName[onclick*='fncChrDetailView']")
        if not links:
            raise CloseSpider("megastudy_selector_changed")

        seen: set[str] = set()
        for link in links:
            title = " ".join(link.css("::text").getall()).strip()
            onclick = link.attrib.get("onclick", "")
            course_id = extract_course_id(onclick)
            if not title or not course_id or course_id in seen:
                continue
            seen.add(course_id)

            row = link.xpath("ancestor::tr[1]")
            series = " ".join(row.xpath("./th[1]//text() | ./td[1]//text()").getall()).strip()
            status = " ".join(link.xpath("ancestor::div[1]/@class").getall()).strip()
            description_parts = [part for part in (series, status) if part]

            item = CurriculumItem()
            item["source_url"] = f"{response.url}#course-{course_id}"
            item["academy_name"] = "메가스터디"
            item["region"] = "온라인"
            item["subject"] = infer_subject(title)
            item["course_title"] = title
            item["description"] = " | ".join(description_parts)
            item["crawled_at"] = datetime.now(timezone.utc).isoformat()
            yield item
