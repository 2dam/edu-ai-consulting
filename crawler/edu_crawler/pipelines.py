import logging

import requests
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)

# 합격수기 등에서 흔히 등장하는 개인 식별 패턴 필드명 — 존재 시 제거.
# 사업계획서 6.1항 "개인정보 비식별화" 대응.
PII_FIELDS = {"student_name", "phone", "email", "school_class", "address"}


class AnonymizePipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field in list(adapter.field_names()):
            if field in PII_FIELDS:
                del adapter[field]
        return item


class ApiExportPipeline:
    """크롤링 결과를 FastAPI 백엔드의 /ingest 엔드포인트로 전송."""

    def open_spider(self, spider):
        self.api_url = spider.settings.get("EXPORT_API_URL")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        payload = {
            "item_type": item.__class__.__name__,
            "data": adapter.asdict(),
        }
        try:
            requests.post(self.api_url, json=payload, timeout=5)
        except requests.RequestException as exc:
            logger.warning("API export failed, dropping to local log only: %s", exc)
        return item
