"""교육 뉴스 스파이더 전용 최소 실행 설정."""

from edu_crawler.settings import *  # noqa: F403


# 전체 spiders 패키지를 순회하지 않아 PDF/브라우저 선택 의존성이 없어도 실행된다.
SPIDER_MODULES = ["edu_crawler.spiders.education_news_spider"]
NEWSPIDER_MODULE = "edu_crawler.spiders"
