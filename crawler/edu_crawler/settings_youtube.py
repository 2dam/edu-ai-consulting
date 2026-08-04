"""입시 YouTube Data API 수집기 전용 최소 실행 설정."""

from edu_crawler.settings import *  # noqa: F403


# 전체 spiders 패키지를 순회하지 않아 PDF·브라우저 선택 의존성과 분리한다.
SPIDER_MODULES = ["edu_crawler.spiders.admission_youtube_spider"]
NEWSPIDER_MODULE = "edu_crawler.spiders"

# 공식 API 응답은 원본 JSON 파일과 범용 /ingest 저장소에 함께 보낼 수 있다.
ROBOTSTXT_OBEY = False
