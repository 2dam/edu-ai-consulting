"""직접 확인한 대학별 공식 입학처 주소 목록."""

from urllib.parse import urlparse


VERIFIED_AT = "2026-08-03"

UNIVERSITY_ADMISSIONS = [
    {
        "id": "snu",
        "university": "서울대학교",
        "campus": "관악캠퍼스",
        "region": "서울",
        "url": "https://admission.snu.ac.kr/",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "yonsei_seoul",
        "university": "연세대학교",
        "campus": "서울캠퍼스",
        "region": "서울",
        "url": "https://admission.yonsei.ac.kr/seoul/admission/html/main/main.asp",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "korea_seoul",
        "university": "고려대학교",
        "campus": "서울캠퍼스",
        "region": "서울",
        "url": "https://oku.korea.ac.kr/",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "skku",
        "university": "성균관대학교",
        "campus": "통합 입학처",
        "region": "서울·경기",
        "url": "https://admission.skku.edu/",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "hanyang_seoul",
        "university": "한양대학교",
        "campus": "서울캠퍼스",
        "region": "서울",
        "url": "https://go.hanyang.ac.kr/gate.do",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "kaist",
        "university": "한국과학기술원(KAIST)",
        "campus": "대전 본원",
        "region": "대전",
        "url": "https://admission.kaist.ac.kr/",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "postech",
        "university": "포항공과대학교(POSTECH)",
        "campus": "포항캠퍼스",
        "region": "경북",
        "url": "https://adm-u.postech.ac.kr/",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "ewha",
        "university": "이화여자대학교",
        "campus": "서울캠퍼스",
        "region": "서울",
        "url": "https://admission.ewha.ac.kr/admission/html/main/main.asp",
        "verified_at": VERIFIED_AT,
    },
    {
        "id": "cau",
        "university": "중앙대학교",
        "campus": "통합 입학처",
        "region": "서울·경기",
        "url": "https://admission.cau.ac.kr/main.do",
        "verified_at": VERIFIED_AT,
    },
]


def validate_registry(entries: list[dict] | None = None) -> None:
    """목록에 대학 공식 HTTPS 주소만 들어 있는지 검사한다."""
    entries = UNIVERSITY_ADMISSIONS if entries is None else entries
    ids: set[str] = set()
    for entry in entries:
        if entry["id"] in ids:
            raise ValueError(f"중복 입학처 ID: {entry['id']}")
        ids.add(entry["id"])

        parsed = urlparse(entry["url"])
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https":
            raise ValueError(f"HTTPS가 아닌 입학처 주소: {entry['url']}")
        if not (hostname.endswith(".ac.kr") or hostname.endswith(".edu")):
            raise ValueError(f"대학 공식 도메인이 아닌 주소: {entry['url']}")


def list_university_admissions(query: str | None = None, region: str | None = None) -> list[dict]:
    validate_registry()
    query_key = (query or "").strip().casefold()
    region_key = (region or "").strip().casefold()

    results = []
    for entry in UNIVERSITY_ADMISSIONS:
        searchable = " ".join((entry["university"], entry["campus"], entry["id"])).casefold()
        if query_key and query_key not in searchable:
            continue
        if region_key and region_key not in entry["region"].casefold():
            continue
        results.append({**entry, "access_mode": "official_link"})
    return results


validate_registry()
