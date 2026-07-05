"""어린이집·유치원·초등학교·학원 기본현황 + 공식 평가/등록 정보 수집 스파이더.

네 시설 유형을 -a facility_type=daycare|kindergarten|elementary|academy 로 선택한다.
"리뷰"는 공식 출처(평가인증·정보공시·등록현황)만 다룬다 — 네이버/카카오 등 민간
리뷰 스크래핑은 이용약관상 금지되어 있어 이 스파이더의 대상이 아니다.

- elementary: 나이스(NEIS) 교육정보 개방포털 Open API (open.neis.go.kr/hub/schoolInfo).
  실서비스이며 인증키만 발급받으면 바로 동작한다. https://open.neis.go.kr 에서 무료 발급.
- daycare / kindergarten / academy: 어린이집정보공개포털(info.childcare.go.kr),
  유치원알리미(e-childschoolinfo.moe.go.kr), 전국학원교습소정보 표준데이터 등은
  공공데이터포털(data.go.kr)의 "공공데이터 개방 표준" REST 포맷
  (response.body.items.item)을 따르는 API로 제공되는 경우가 많다.
  -a portal_url=<data.go.kr 활용신청 후 발급받은 실제 엔드포인트> 로 지정하면
  표준 포맷으로 파싱한다.
  주의: 기관마다 응답 필드명이 다르므로 FIELD_MAP 은 실제 활용신청 후 받은 응답
  스키마를 확인하고 채워 넣을 것 — academy_spider/public_data_spider 의 CSS 셀렉터와
  동일하게 "확인 후 채우는" placeholder다 (README "아직 안 한 것" 항목 참고).

실행 예:
  scrapy crawl early_education -a facility_type=elementary -a region_code=B10 -a region_name=서울
  scrapy crawl early_education -a facility_type=daycare -a portal_url="https://apis.data.go.kr/..." -a service_key=...
  scrapy crawl early_education -a facility_type=academy -a portal_url="https://apis.data.go.kr/..." -a service_key=... -a region_name=전국
"""
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import scrapy

from edu_crawler.items import EducationFacilityItem

NEIS_SCHOOL_INFO_URL = "https://open.neis.go.kr/hub/schoolInfo"

# 공공데이터포털 응답의 item 필드명 -> EducationFacilityItem 필드명.
# 실제 신청한 API의 응답을 확인한 뒤 정확한 키로 수정할 것 (기관별로 상이).
FIELD_MAP = {
    "daycare": {
        "name": "crname",
        "address": "craddr",
        "capacity": "crcapat",
        "current_enrollment": "crchcnt",
        "establishment_type": "crtypename",
        "evaluation_grade": "crgraderesultname",  # 어린이집평가제 등급 (최우수/우수/A/B/C 등)
    },
    "kindergarten": {
        "name": "schul_nm",
        "address": "org_rdnma",
        "establishment_type": "fond_sc_nm",
    },
    "academy": {
        # 전국학원교습소정보 표준데이터 (data.go.kr) 기준 — 실제 응답 필드명 확인 후 수정
        "name": "academyname",
        "address": "roadnameaddress",
        "establishment_type": "coursename",       # 교습과정 (예: 수학·영어·입시 등)
        "status_note": "registrationstatusname",  # 등록상태 (정상/휴원/폐원 등)
    },
}


class EarlyEducationSpider(scrapy.Spider):
    name = "early_education"

    def __init__(self, facility_type="elementary", region_code=None, region_name="",
                 portal_url=None, service_key=None, page_size=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if facility_type not in ("daycare", "kindergarten", "elementary", "academy"):
            raise ValueError("usage: -a facility_type=daycare|kindergarten|elementary|academy")
        self.facility_type = facility_type
        self.region_code = region_code
        self.region_name = region_name
        self.portal_url = portal_url
        self.service_key = service_key
        self.page_size = int(page_size)

    def start_requests(self):
        if self.facility_type == "elementary":
            params = {"Type": "json", "pIndex": 1, "pSize": self.page_size, "SCHUL_KND_SC_NM": "초등학교"}
            neis_key = os.environ.get("NEIS_API_KEY", "")
            if neis_key:
                params["KEY"] = neis_key
            if self.region_code:
                params["ATPT_OFCDC_SC_CODE"] = self.region_code
            url = f"{NEIS_SCHOOL_INFO_URL}?{urlencode(params)}"
            yield scrapy.Request(url, callback=self.parse_neis)
        else:
            if not self.portal_url:
                raise ValueError(
                    "daycare/kindergarten 모드는 -a portal_url=<공공데이터포털 활용신청 엔드포인트> 가 필요합니다"
                )
            service_key = self.service_key or os.environ.get("DATA_GO_KR_SERVICE_KEY", "")
            params = {"serviceKey": service_key, "type": "json", "numOfRows": self.page_size, "pageNo": 1}
            sep = "&" if "?" in self.portal_url else "?"
            url = f"{self.portal_url}{sep}{urlencode(params)}"
            yield scrapy.Request(url, callback=self.parse_public_data_standard)

    def parse_neis(self, response):
        now = datetime.now(timezone.utc).isoformat()
        try:
            payload = response.json()
        except ValueError:
            self.logger.error("NEIS 응답 파싱 실패: %s", response.text[:300])
            return

        neis_block = payload.get("schoolInfo")
        rows = neis_block[1].get("row", []) if isinstance(neis_block, list) and len(neis_block) > 1 else []
        for row in rows:
            item = EducationFacilityItem()
            item["source_url"] = response.url
            item["facility_type"] = "elementary"
            item["name"] = row.get("SCHUL_NM", "")
            item["region"] = row.get("LCTN_SC_NM", "") or self.region_name
            item["district"] = ""
            item["address"] = row.get("ORG_RDNMA", "")
            item["establishment_type"] = row.get("FOND_SC_NM", "")
            item["capacity"] = None
            item["current_enrollment"] = None
            item["teacher_count"] = None
            item["evaluation_grade"] = ""
            item["status_note"] = ""
            item["crawled_at"] = now
            if item["name"]:
                yield item

    def parse_public_data_standard(self, response):
        """공공데이터포털 표준 응답 포맷(response.body.items.item)을 파싱한다."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            payload = response.json()
        except ValueError:
            self.logger.error("%s 응답 파싱 실패: %s", self.facility_type, response.text[:300])
            return

        body = payload.get("response", {}).get("body", {})
        raw_items = body.get("items", {})
        rows = raw_items.get("item", []) if isinstance(raw_items, dict) else raw_items
        if isinstance(rows, dict):
            rows = [rows]

        field_map = FIELD_MAP.get(self.facility_type, {})
        for row in rows or []:
            item = EducationFacilityItem()
            item["source_url"] = response.url
            item["facility_type"] = self.facility_type
            item["name"] = row.get(field_map.get("name", "name"), "")
            item["region"] = self.region_name
            item["district"] = ""
            item["address"] = row.get(field_map.get("address", "address"), "")
            item["establishment_type"] = row.get(field_map.get("establishment_type", "type"), "")
            item["capacity"] = row.get(field_map.get("capacity", "capacity"))
            item["current_enrollment"] = row.get(field_map.get("current_enrollment", "enrollment"))
            item["teacher_count"] = None
            item["evaluation_grade"] = row.get(field_map.get("evaluation_grade", "evaluation_grade"), "")
            item["status_note"] = row.get(field_map.get("status_note", "status_note"), "")
            item["crawled_at"] = now
            if item["name"]:
                yield item
