
"""NEIS 학원·학교 수집기 전용 최소 실행 설정."""

from edu_crawler.settings import *  # noqa: F403


SPIDER_MODULES = ["edu_crawler.spiders.early_education_spider"]
NEWSPIDER_MODULE = "edu_crawler.spiders"
TELNETCONSOLE_ENABLED = False
