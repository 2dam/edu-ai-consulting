"""전국 17개 시도교육청의 공식 진로·진학 지원 서비스 목록."""

from urllib.parse import urlparse


VERIFIED_AT = "2026-08-03"

CAREER_GUIDANCE_CENTERS = [
    {"id": "seoul", "region": "서울", "name": "서울진로진학정보센터", "url": "https://www.jinhak.or.kr/"},
    {"id": "busan", "region": "부산", "name": "부산진로진학지원센터", "url": "https://dream.pen.go.kr/"},
    {"id": "daegu", "region": "대구", "name": "대구진학진로정보센터", "url": "https://www.dge.go.kr/jinhak/main.do"},
    {"id": "incheon", "region": "인천", "name": "인천사이버진로교육원", "url": "https://cyberjinro.ice.go.kr/"},
    {"id": "gwangju", "region": "광주", "name": "광주진로진학지원센터", "url": "https://jinhak.gen.go.kr/"},
    {"id": "daejeon", "region": "대전", "name": "대전진로융합교육원", "url": "https://www.edurang.net/course/main.do"},
    {"id": "ulsan", "region": "울산", "name": "울산진로진학지원센터", "url": "https://use.go.kr/jinhak/"},
    {"id": "sejong", "region": "세종", "name": "세종진로교육원", "url": "https://jinro.sje.go.kr/"},
    {"id": "gyeonggi", "region": "경기", "name": "경기진학정보센터", "url": "https://more.goe.go.kr/jinhak/"},
    {"id": "gangwon", "region": "강원", "name": "강원진학지원센터", "url": "https://jinhak.gwe.go.kr/"},
    {"id": "chungbuk", "region": "충북", "name": "충청북도진로교육원", "url": "https://jinro.cbe.go.kr/"},
    {"id": "chungnam", "region": "충남", "name": "충남진학있슈", "url": "https://jinhak.cne.go.kr/"},
    {"id": "jeonbuk", "region": "전북", "name": "전북진로진학센터", "url": "https://www.jbe.go.kr/jinro/"},
    {"id": "jeonnam", "region": "전남", "name": "전남진로진학지원포털", "url": "https://jdream.jne.go.kr/"},
    {"id": "gyeongbuk", "region": "경북", "name": "경북진학지원센터", "url": "https://www.gbe.kr/jinhak/"},
    {"id": "gyeongnam", "region": "경남", "name": "경남대입정보센터", "url": "https://jinhak.gne.go.kr/"},
    {"id": "jeju", "region": "제주", "name": "제주진로진학지원센터", "url": "https://jinhak.jje.go.kr/"},
]

ALLOWED_HOSTS = {
    "www.jinhak.or.kr", "dream.pen.go.kr", "www.dge.go.kr", "cyberjinro.ice.go.kr",
    "jinhak.gen.go.kr", "www.edurang.net", "use.go.kr", "jinro.sje.go.kr",
    "more.goe.go.kr", "jinhak.gwe.go.kr", "jinro.cbe.go.kr", "jinhak.cne.go.kr",
    "www.jbe.go.kr", "jdream.jne.go.kr", "www.gbe.kr", "jinhak.gne.go.kr",
    "jinhak.jje.go.kr",
}

# 이번 검토에서 실제 페이지 내용 또는 현재 리디렉션까지 확인한 지역.
# 나머지는 교육청이 발행한 전국 센터 공식 목록을 기준으로 등재한다.
LIVE_CHECKED_IDS = {"busan", "daegu", "daejeon", "chungbuk", "chungnam"}


def validate_registry(entries: list[dict] | None = None) -> None:
    entries = CAREER_GUIDANCE_CENTERS if entries is None else entries
    ids: set[str] = set()
    regions: set[str] = set()
    for entry in entries:
        if entry["id"] in ids:
            raise ValueError(f"중복 센터 ID: {entry['id']}")
        if entry["region"] in regions:
            raise ValueError(f"중복 시도: {entry['region']}")
        ids.add(entry["id"])
        regions.add(entry["region"])

        parsed = urlparse(entry["url"])
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ValueError(f"검증되지 않은 센터 주소: {entry['url']}")


def list_career_guidance_centers(query: str | None = None, region: str | None = None) -> list[dict]:
    validate_registry()
    query_key = (query or "").strip().casefold()
    region_key = (region or "").strip().casefold()
    results = []
    for center in CAREER_GUIDANCE_CENTERS:
        if query_key and query_key not in f"{center['name']} {center['region']}".casefold():
            continue
        if region_key and region_key != center["region"].casefold():
            continue
        results.append(
            {
                **center,
                "verified_at": VERIFIED_AT,
                "verification_status": "live_checked" if center["id"] in LIVE_CHECKED_IDS else "official_directory",
                "access_mode": "official_link",
            }
        )
    return results


validate_registry()
