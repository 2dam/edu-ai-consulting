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
