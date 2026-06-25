"""
공공 데이터(학교알리미, 대학 입학처 공시자료, 교육부 보도자료 등)에서
입시 결과·정책 데이터를 수집하는 스파이더.

공공 데이터는 대체로 크롤링 제약이 적지만, 가능하면 공공데이터포털
(data.go.kr) Open API 사용을 우선 검토할 것 (계획서 6.1항 권고).

실행 예:
  scrapy crawl public_data -a start_url="https://www.schoolinfo.go.kr/..." -a item_kind="admission"
"""
from datetime import datetime, timezone

import scrapy

from edu_crawler.items import AdmissionResultItem, PolicyNewsItem


class PublicDataSpider(scrapy.Spider):
    name = "public_data"

    def __init__(self, start_url=None, item_kind="admission", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url:
            raise ValueError("usage: -a start_url=<공시자료 URL> -a item_kind=admission|policy")
        self.start_urls = [start_url]
        self.item_kind = item_kind

    def parse(self, response):
        now = datetime.now(timezone.utc).isoformat()

        if self.item_kind == "policy":
            for row in response.css(".board-list tr, .news-item"):
                item = PolicyNewsItem()
                item["source_url"] = response.urljoin(row.css("a::attr(href)").get(default=""))
                item["title"] = row.css("a::text, .title::text").get(default="").strip()
                item["published_at"] = row.css(".date::text").get(default="").strip()
                item["summary"] = row.css(".summary::text").get(default="").strip()
                item["crawled_at"] = now
                if item["title"]:
                    yield item
        else:
            for row in response.css(".result-table tr, .admission-row"):
                item = AdmissionResultItem()
                item["source_url"] = response.url
                item["university"] = row.css(".university::text").get(default="").strip()
                item["department"] = row.css(".department::text").get(default="").strip()
                item["year"] = row.css(".year::text").get(default="").strip()
                item["admission_type"] = row.css(".admission-type::text").get(default="").strip()
                item["competition_rate"] = row.css(".competition-rate::text").get(default="").strip()
                item["cutoff_score"] = row.css(".cutoff-score::text").get(default="").strip()
                item["crawled_at"] = now
                if item["university"]:
                    yield item
