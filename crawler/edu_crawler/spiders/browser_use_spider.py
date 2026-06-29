"""
Browser Use AI 에이전트 기반 학원 크롤러.

CSS 셀렉터를 미리 몰라도 LLM이 직접 브라우저를 조작해 과정 정보를 추출한다.
Scrapy 스파이더로 수집하기 어려운 JS-heavy 사이트나
구조를 미리 알 수 없는 신규 학원 사이트에 사용.

수집한 결과는 academy_spider와 동일한 CurriculumItem 형태로
백엔드 /ingest 엔드포인트에 전송한다.

필수 환경변수:
  ANTHROPIC_API_KEY  — Claude API 키

실행 예:
  cd crawler
  python -m edu_crawler.spiders.browser_use_spider \\
    --url "https://www.example-academy.co.kr" \\
    --academy "예시학원" --region "서울"

  # JSON 파일로 저장만:
  python -m edu_crawler.spiders.browser_use_spider \\
    --url "https://www.example-academy.co.kr" \\
    --academy "예시학원" --output result.json --no-api
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

import requests as _requests

logger = logging.getLogger(__name__)

_TASK_TEMPLATE = """\
다음 학원 웹사이트에서 공개된 수업/과정 정보를 수집해 주세요.
URL: {url}

수집 절차:
1. 먼저 메인 페이지를 열고 메뉴/네비게이션에서 과정 목록 링크를 찾으세요.
2. 각 과정 상세 페이지를 방문해 커리큘럼 내용을 읽으세요.
3. 아래 형식의 JSON 배열을 최종 결과로 반환하세요.

주의 사항:
- 학생 이름, 전화번호, 이메일, 주소 등 개인정보는 절대 포함하지 마세요.
- 과정명과 커리큘럼 내용만 수집하세요.
- 정보가 전혀 없으면 [] 를 반환하세요.
- 반드시 유효한 JSON 배열만 반환하세요 (다른 텍스트 없이).

반환 형식:
[
  {{
    "course_title": "과정명 (예: 수능 수학 집중반)",
    "subject": "과목 (수학/영어/국어/과학/사회 등, 알 수 없으면 빈 문자열)",
    "description": "과정 설명, 커리큘럼, 특징, 수업 방식 등 (가능한 한 상세하게)"
  }}
]
"""


def _extract_json(raw: str) -> list:
    """LLM 응답 텍스트에서 JSON 배열을 추출한다."""
    if not raw:
        return []

    # 마크다운 코드 블록 제거
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                data = json.loads(part)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue

    # 직접 파싱 시도
    raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start != -1 and end > start:
        try:
            data = json.loads(raw[start:end])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return []


async def crawl_with_browser_use(url: str, academy_name: str, region: str) -> list[dict]:
    from browser_use import Agent
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        temperature=0,
    )
    agent = Agent(
        task=_TASK_TEMPLATE.format(url=url),
        llm=llm,
    )

    logger.info("Browser Use 에이전트 시작: %s", url)
    result = await agent.run()
    raw = result.final_result() or "[]"
    logger.info("에이전트 완료. 원본 결과 길이: %d자", len(raw))

    courses = _extract_json(raw)
    now = datetime.now(timezone.utc).isoformat()

    return [
        {
            "source_url": url,
            "academy_name": academy_name,
            "region": region,
            "subject": c.get("subject", ""),
            "course_title": c.get("course_title", ""),
            "description": c.get("description", ""),
            "crawled_at": now,
        }
        for c in courses
        if c.get("course_title")
    ]


def _post_to_api(items: list[dict], api_url: str) -> None:
    for item in items:
        payload = {"item_type": "CurriculumItem", "data": item}
        try:
            _requests.post(api_url, json=payload, timeout=5)
        except _requests.RequestException as exc:
            logger.warning("API 전송 실패: %s", exc)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Browser Use AI 학원 크롤러")
    parser.add_argument("--url", required=True, help="학원 홈페이지 URL")
    parser.add_argument("--academy", required=True, help="학원 이름")
    parser.add_argument("--region", default="unknown", help="지역 (기본: unknown)")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/ingest",
        help="결과 전송 API URL (기본: http://localhost:8000/ingest)",
    )
    parser.add_argument("--output", default=None, help="JSON 파일 저장 경로")
    parser.add_argument(
        "--no-api", action="store_true", help="API 전송 없이 파일/stdout만 출력"
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("오류: ANTHROPIC_API_KEY 환경변수를 설정하세요.", file=sys.stderr)
        sys.exit(1)

    items = asyncio.run(crawl_with_browser_use(args.url, args.academy, args.region))
    logger.info("수집 완료: %d개 과정", len(items))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info("저장: %s", args.output)
    elif not items or args.no_api:
        print(json.dumps(items, ensure_ascii=False, indent=2))

    if not args.no_api:
        _post_to_api(items, args.api_url)
        logger.info("API 전송 완료: %s", args.api_url)


if __name__ == "__main__":
    main()
