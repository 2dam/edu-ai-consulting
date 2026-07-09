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
    """크롤링 결과를 FastAPI 백엔드의 /ingest-batch 엔드포인트로 일괄 전송.

    학원 등 건수가 많은(10만+) 크롤에서 건별 요청 왕복 비용이 지배적이라
    BATCH_SIZE개씩 모아 한 번에 보낸다. /ingest-batch가 없는 구버전 배포와의
    호환을 위해 실패 시 건별 /ingest로 폴백한다.
    """

    BATCH_SIZE = 50

    def open_spider(self, spider):
        self.api_url = spider.settings.get("EXPORT_API_URL")
        self.batch_url = self.api_url.replace("/ingest", "/ingest-batch")
        self.buffer = []

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        self.buffer.append({
            "item_type": item.__class__.__name__,
            "data": adapter.asdict(),
        })
        if len(self.buffer) >= self.BATCH_SIZE:
            self._flush()
        return item

    def close_spider(self, spider):
        self._flush()

    def _flush(self):
        if not self.buffer:
            return
        batch, self.buffer = self.buffer, []
        try:
            requests.post(self.batch_url, json=batch, timeout=30)
        except requests.RequestException as exc:
            logger.warning("배치 전송 실패, 건별 전송으로 재시도: %s", exc)
            for payload in batch:
                try:
                    requests.post(self.api_url, json=payload, timeout=5)
                except requests.RequestException as exc2:
                    logger.warning("API export failed, dropping to local log only: %s", exc2)
