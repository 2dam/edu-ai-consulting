"""
Scrapling 기반 봇 차단 우회 미들웨어.

Scrapy가 HTML 응답을 정상적으로 받지 못할 때 Scrapling으로 재시도한다.

요청 메타로 직접 지정:
  meta={'use_scrapling': True}            → 스텔스 HTTP (TLS 핑거프린트 우회, 빠름)
  meta={'use_scrapling_playwright': True} → 브라우저 자동화 (JS 렌더링 + Cloudflare Turnstile 우회)

자동 트리거: HTML 응답이 403/429/503이거나 본문 500B 미만(빈 차단 페이지 의심)이면
Playwright로 자동 재시도. PDF·엑셀 등 바이너리 응답은 건너뜀.

AsyncioSelectorReactor를 사용하는 이 프로젝트에서 async 미들웨어가 지원된다(Scrapy 2.0+).
"""
import logging

from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

_BLOCK_STATUSES = {403, 429, 503}
_BODY_TOO_SMALL = 500


class ScraplingFallbackMiddleware:
    """Scrapy 응답이 봇 차단을 받으면 Scrapling으로 재시도한다."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    async def process_response(self, request, response, spider):
        force_playwright = request.meta.get("use_scrapling_playwright", False)
        force_stealth = request.meta.get("use_scrapling", False)

        # 바이너리 콘텐츠(PDF, 엑셀 등)는 건너뜀
        content_type = (
            response.headers.get("Content-Type", b"")
            .decode("utf-8", errors="ignore")
            .lower()
        )
        is_html = (
            "text/html" in content_type
            or "application/xhtml" in content_type
            or not content_type
        )

        is_blocked = is_html and (
            response.status in _BLOCK_STATUSES
            or (response.status == 200 and len(response.body) < _BODY_TOO_SMALL)
        )

        if not force_playwright and not force_stealth and not is_blocked:
            return response

        if not is_html and not force_playwright and not force_stealth:
            return response

        use_playwright = force_playwright or is_blocked

        try:
            if use_playwright:
                # DynamicFetcher: Playwright 기반, 봇 감지 우회 + JS 렌더링
                from scrapling import DynamicFetcher

                fetcher = DynamicFetcher()
                logger.info("[Scrapling] Playwright 재시도: %s", request.url)
                page = await fetcher.async_fetch(request.url)
            else:
                # AsyncFetcher: curl_cffi 기반 스텔스 HTTP
                from scrapling.fetchers import AsyncFetcher

                fetcher = AsyncFetcher()
                logger.info("[Scrapling] 스텔스 HTTP 재시도: %s", request.url)
                page = await fetcher.get(request.url)

            # Scrapling Selector.get() → 루트 HTML 문자열
            html = page.get() or ""
            if not html:
                logger.warning("[Scrapling] HTML 추출 실패 (%s) — 원본 응답 사용", request.url)
                return response

            return HtmlResponse(
                url=request.url,
                body=html.encode("utf-8"),
                encoding="utf-8",
                request=request,
            )
        except Exception as exc:
            logger.warning(
                "[Scrapling] 재시도 실패 (%s): %s — 원본 응답 사용", request.url, exc
            )
            return response
