BOT_NAME = "edu_crawler"

SPIDER_MODULES = ["edu_crawler.spiders"]
NEWSPIDER_MODULE = "edu_crawler.spiders"

# 사업계획서 6.1항 "데이터 수집 합법성" 준수 — robots.txt 강제 적용.
# 개별 스파이더에서 끄지 말 것.
ROBOTSTXT_OBEY = True

# 대상 서버 부담을 줄이기 위한 보수적 기본값. 사이트 운영자에게 부담을 주지 않도록 유지.
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

USER_AGENT = "EduAIConsultingBot/0.1 (+contact: jincheondong9@gmail.com)"

# --- Scrapling 봇 차단 우회 미들웨어 ---
# 우선순위 543: Scrapy 기본 RetryMiddleware(550) 직전에 실행.
# 403/503 응답 또는 요청 메타에 use_scrapling/use_scrapling_playwright가 있을 때만 개입.
DOWNLOADER_MIDDLEWARES = {
    "edu_crawler.middlewares.ScraplingFallbackMiddleware": 543,
}

ITEM_PIPELINES = {
    "edu_crawler.pipelines.AnonymizePipeline": 100,
    "edu_crawler.pipelines.ApiExportPipeline": 200,
}

# 백엔드 API로 결과를 전송할 주소 (api/app/main.py 의 /ingest 엔드포인트)
EXPORT_API_URL = "http://localhost:8000/ingest"

LOG_LEVEL = "INFO"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
