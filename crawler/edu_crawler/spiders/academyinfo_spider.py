"""대학알리미 공식 OpenAPI의 대학 기본정보 수집기.

공공데이터포털 활용신청 후 발급받은 DATA_GO_KR_SERVICE_KEY가 필요하다. 대학알리미
웹페이지 HTML을 수집하지 않고, 이용허락범위 제한 없음으로 공개된 공식 API만 사용한다.

실행:
  scrapy crawl academyinfo_universities -O universities.json
"""

import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import scrapy

from edu_crawler.items import EducationFacilityItem

API_BASE = "https://apis.data.go.kr/B340014/BasicInformationService_2"
UNIVERSITY_CODE_ENDPOINT = f"{API_BASE}/getUniversityCode"

FIELD_ALIASES = {
    "name": ("univNm", "schlNm", "univName", "schoolName", "대학명"),
    "code": ("univCd", "schlCd", "univCode", "schoolCode", "대학코드"),
    "region": ("regionNm", "sidoNm", "regionName", "지역명"),
    "district": ("sigunguNm", "districtNm", "시군구명"),
    "address": ("addr", "address", "roadAddr", "주소"),
    "founding": ("foundNm", "estbType", "foundingType", "설립유형"),
    "school_type": ("typeNm", "schlTypeNm", "schoolType", "학교유형"),
}


def first_value(values: dict[str, str], aliases: tuple[str, ...]) -> str:
    return next((values[key].strip() for key in aliases if values.get(key, "").strip()), "")


class AcademyInfoUniversitySpider(scrapy.Spider):
    name = "academyinfo_universities"
    allowed_domains = ["apis.data.go.kr"]
    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOADER_MIDDLEWARES": {
            "edu_crawler.middlewares.ScraplingFallbackMiddleware": None,
            # 공식 API에는 웹사이트용 robots middleware를 적용하지 않는다.
            "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": None,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
        if not self.api_key:
            raise ValueError("DATA_GO_KR_SERVICE_KEY 환경변수가 필요합니다")

    def start_requests(self):
        query = urlencode({"serviceKey": self.api_key, "pageNo": 1, "numOfRows": 1000})
        yield scrapy.Request(f"{UNIVERSITY_CODE_ENDPOINT}?{query}", callback=self.parse)

    def parse(self, response):
        result_code = response.xpath("string(//*[local-name()='resultCode'][1])").get(default="").strip()
        result_message = response.xpath("string(//*[local-name()='resultMsg'][1])").get(default="").strip()
        if result_code and result_code not in {"00", "0", "NORMAL_SERVICE"}:
            raise ValueError(f"대학알리미 API 오류 {result_code}: {result_message}")

        rows = response.xpath("//*[local-name()='item']")
        if not rows:
            rows = response.xpath("//*[local-name()='row']")
        if not rows:
            self.logger.error("대학알리미 응답에 대학 행이 없습니다. API 명세/키 승인을 확인하세요.")
            return

        for row in rows:
            values = {
                node.xpath("local-name()").get(): " ".join(node.xpath(".//text()").getall()).strip()
                for node in row.xpath("./*")
            }
            name = first_value(values, FIELD_ALIASES["name"])
            if not name:
                continue
            university_code = first_value(values, FIELD_ALIASES["code"])

            item = EducationFacilityItem()
            item["source_url"] = (
                f"https://www.academyinfo.go.kr/search/search.do?query={university_code}"
                if university_code else "https://www.academyinfo.go.kr/"
            )
            item["facility_type"] = "university"
            item["name"] = name
            item["region"] = first_value(values, FIELD_ALIASES["region"])
            item["district"] = first_value(values, FIELD_ALIASES["district"])
            item["address"] = first_value(values, FIELD_ALIASES["address"])
            item["lat"] = ""
            item["lng"] = ""
            item["establishment_type"] = first_value(values, FIELD_ALIASES["founding"])
            item["capacity"] = ""
            item["current_enrollment"] = ""
            item["teacher_count"] = ""
            item["evaluation_grade"] = ""
            school_type = first_value(values, FIELD_ALIASES["school_type"])
            item["status_note"] = " | ".join(
                part for part in (f"대학코드: {university_code}" if university_code else "", school_type) if part
            )
            item["crawled_at"] = datetime.now(timezone.utc).isoformat()
            yield item
