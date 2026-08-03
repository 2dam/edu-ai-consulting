"""입시 전문가용 공식 원문 출처 레지스트리.

저작권 또는 이용조건상 재수집이 허용되지 않은 사이트는 콘텐츠를 복제하지 않고 링크와
확인 목적만 제공한다. 데이터 수집 API가 있는 출처는 integration 값을 함께 노출한다.
"""

OFFICIAL_ADMISSION_SOURCES = [
    {
        "id": "adiga",
        "name": "대입정보포털 어디가",
        "operator": "한국대학교육협의회",
        "url": "https://www.adiga.kr/",
        "purposes": ["대학정보", "학과정보", "전형정보", "대학별 전형결과", "공식 대입상담"],
        "access_mode": "link_only",
        "integration": None,
        "notice": "저작권정책상 콘텐츠를 복제하지 않습니다. 최종 모집요강은 대학 입학처에서 다시 확인하세요.",
    },
    {
        "id": "academyinfo",
        "name": "대학알리미",
        "operator": "한국대학교육협의회 대학정보공시센터",
        "url": "https://www.academyinfo.go.kr/",
        "purposes": ["대학 기본정보", "학생·교원 현황", "등록금", "교육여건", "취업률"],
        "access_mode": "official_api",
        "integration": "academyinfo_universities",
        "notice": "공공데이터포털 공식 API를 사용합니다.",
    },
    {
        "id": "career_net",
        "name": "진로정보망 커리어넷",
        "operator": "교육부·한국직업능력연구원",
        "url": "https://www.career.go.kr/",
        "purposes": ["학과정보", "직업정보", "진로교육자료", "진로상담사례"],
        "access_mode": "official_api",
        "integration": "pending_careernet_api",
        "notice": "공식 Open API 인증키가 필요한 출처입니다.",
    },
    {
        "id": "university_admissions",
        "name": "대학별 입학처",
        "operator": "각 대학",
        "url": None,
        "purposes": ["최종 모집요강", "원서접수 일정", "전형 변경사항", "합격자 발표"],
        "access_mode": "institution_registry",
        "integration": "pending_admissions_registry",
        "notice": "대학별 공식 도메인을 검증한 레지스트리로 제공할 예정입니다.",
    },
]


def list_official_sources() -> list[dict]:
    return [dict(source) for source in OFFICIAL_ADMISSION_SOURCES]
