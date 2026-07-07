import scrapy


class CurriculumItem(scrapy.Item):
    """사업계획서 3.1항 '학원 커리큘럼' 데이터 유형."""

    source_url = scrapy.Field()
    academy_name = scrapy.Field()
    region = scrapy.Field()
    subject = scrapy.Field()
    course_title = scrapy.Field()
    description = scrapy.Field()
    crawled_at = scrapy.Field()


class AdmissionResultItem(scrapy.Item):
    """사업계획서 3.1항 '입시 결과 데이터' 유형 (대학 공시·학교알리미 등 공개 자료 기준)."""

    source_url = scrapy.Field()
    university = scrapy.Field()
    department = scrapy.Field()
    year = scrapy.Field()
    admission_type = scrapy.Field()
    competition_rate = scrapy.Field()
    cutoff_score = scrapy.Field()
    crawled_at = scrapy.Field()


class SnsAccountItem(scrapy.Item):
    """aliens_eye_runner 가 발견한 학원 공식 SNS 계정 정보.
    sns_content_spider 의 시작점으로 사용된다."""

    source_url = scrapy.Field()    # SNS 계정 URL
    platform = scrapy.Field()      # instagram / youtube / naverblog 등
    username = scrapy.Field()
    academy_name = scrapy.Field()
    region = scrapy.Field()
    crawled_at = scrapy.Field()


class SnsPostItem(scrapy.Item):
    """SNS 공개 게시물에서 수집한 콘텐츠 (커리큘럼·합격 실적 언급 등)."""

    source_url = scrapy.Field()
    platform = scrapy.Field()
    academy_name = scrapy.Field()
    region = scrapy.Field()
    post_title = scrapy.Field()
    post_body = scrapy.Field()
    published_at = scrapy.Field()
    hashtags = scrapy.Field()
    crawled_at = scrapy.Field()


class PolicyNewsItem(scrapy.Item):
    """사업계획서 3.1항 '교육 정책 데이터' 유형."""

    source_url = scrapy.Field()
    title = scrapy.Field()
    published_at = scrapy.Field()
    summary = scrapy.Field()
    crawled_at = scrapy.Field()


class EducationNewsItem(scrapy.Item):
    """AI 교육 뉴스 커뮤니티 모듈용 — 공개 교육 뉴스 기사 (api의 NewsPost와 대응).

    로그인이 필요한 커뮤니티/사설 카페는 대상이 아니며, 공개적으로 열람 가능한
    교육 뉴스 매체만 수집한다."""

    title = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    published_at = scrapy.Field()
    category = scrapy.Field()
    body_text = scrapy.Field()
    thumbnail_url = scrapy.Field()
    region = scrapy.Field()
    tags = scrapy.Field()
    crawled_at = scrapy.Field()


class EducationFacilityItem(scrapy.Item):
    """어린이집·유치원·초등학교·학원 기본현황 + 공식 평가/등록 정보.

    "리뷰" 대신 공식 출처(평가인증·정보공시·등록현황)만 다룬다 — 네이버/카카오 등
    민간 리뷰 스크래핑은 이용약관상 금지되어 있어 취급하지 않는다.

    facility_type: "daycare"(어린이집) | "kindergarten"(유치원)
                 | "elementary"(초등학교) | "academy"(학원)
    """

    source_url = scrapy.Field()
    facility_type = scrapy.Field()
    name = scrapy.Field()
    region = scrapy.Field()          # 시도
    district = scrapy.Field()        # 시군구
    address = scrapy.Field()
    lat = scrapy.Field()
    lng = scrapy.Field()
    establishment_type = scrapy.Field()  # 국공립/사립/직장/가정 등 (학원은 등록과정 구분)
    capacity = scrapy.Field()            # 정원
    current_enrollment = scrapy.Field()  # 현원
    teacher_count = scrapy.Field()
    evaluation_grade = scrapy.Field()    # 어린이집평가제 등급 등 (해당 시)
    status_note = scrapy.Field()         # 등록상태·행정처분 이력 요약 (학원 등)
    crawled_at = scrapy.Field()
