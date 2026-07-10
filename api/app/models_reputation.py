"""
"학원 평판 인텔리전스" 모듈의 DB 모델.

기존 app.models / app.models_community와 별개 파일로 분리하되 같은 Base/engine을
공유한다. main.py에서 이 모듈을 import하기만 하면 Base.metadata.create_all()이
아래 테이블을 모두 인식한다.

1단계(MVP) 범위: 학원 등록, 공개 소스 URL 등록(수동), 학부모·학생 설문, 학원 운영
월간 지표 CSV 업로드, 규칙 기반 평판 점수.

2단계: SNS 공개 게시물 언급(AcademyMention) 추가 — 크롤링 자체는 crawler/ 쪽 별도
프로세스(로컬 CLI)가 담당하고, 여기서는 이미 RawRecord로 들어온 SnsPostItem을
동기화·감성점수화한 결과만 저장한다. 경쟁 학원 비교/평판 예측은 기존 테이블
(ReputationScore, AcademyMonthlyMetric)만으로 계산하므로 별도 테이블이 필요 없다.
이의제기(appeals) 등은 여전히 범위 밖.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, enum.Enum):
    HOMEPAGE = "homepage"
    BLOG = "blog"
    MAP_REVIEW = "map_review"
    NEWS = "news"
    OTHER = "other"


class RespondentType(str, enum.Enum):
    PARENT = "parent"
    STUDENT = "student"


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Academy(Base):
    """평판 분석 대상 학원."""

    __tablename__ = "academies"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(64), unique=True, index=True)  # 예: ACADEMY-SEOUL-GANGNAM-0001
    name = Column(String(200), index=True)
    region = Column(String(100), nullable=True)
    subjects = Column(String(200), nullable=True)  # 콤마 구분 (예: "수학,영어")
    academy_type = Column(String(50), nullable=True)  # 종합/단과/입시/보습 등
    target_grades = Column(String(100), nullable=True)  # 예: "초등,중등"
    edu_office_reg_no = Column(String(100), nullable=True)  # 교육청 등록번호
    created_at = Column(DateTime, default=_now)

    sources = relationship("AcademySource", back_populates="academy", cascade="all, delete-orphan")
    surveys = relationship("SurveyCampaign", back_populates="academy", cascade="all, delete-orphan")
    metrics = relationship("AcademyMonthlyMetric", back_populates="academy", cascade="all, delete-orphan")
    scores = relationship("ReputationScore", back_populates="academy", cascade="all, delete-orphan")
    mentions = relationship("AcademyMention", back_populates="academy", cascade="all, delete-orphan")


class AcademySource(Base):
    """관리자가 등록한 학원 관련 공개 URL (자동 크롤링 없이 링크만 보관)."""

    __tablename__ = "academy_sources"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), index=True)
    source_type = Column(Enum(SourceType), default=SourceType.OTHER)
    url = Column(String(512))
    created_at = Column(DateTime, default=_now)

    academy = relationship("Academy", back_populates="sources")


class SurveyCampaign(Base):
    """학원별 학부모·학생 설문 캠페인. token으로 QR/링크 공개 접근."""

    __tablename__ = "survey_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), index=True)
    token = Column(String(64), unique=True, index=True)
    title = Column(String(200), default="학부모·학생 만족도 조사")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
    closes_at = Column(DateTime, nullable=True)

    academy = relationship("Academy", back_populates="surveys")
    responses = relationship("SurveyResponse", back_populates="campaign", cascade="all, delete-orphan")


class SurveyResponse(Base):
    """설문 응답 1건. answers는 문항별 점수/자유의견을 담은 JSON.

    기대 키: class_satisfaction, teacher_satisfaction, homework_mgmt,
    counseling_satisfaction, improvement_felt, price_satisfaction (각 1~5),
    nps (0~10, 추천의향), renewal_intent (bool), free_text (str, optional).
    """

    __tablename__ = "survey_responses"
    __table_args__ = (UniqueConstraint("campaign_id", "client_fingerprint", name="uq_campaign_fingerprint"),)

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("survey_campaigns.id"), index=True)
    respondent_type = Column(Enum(RespondentType), default=RespondentType.PARENT)
    answers = Column(JSON)
    # 완벽한 중복 차단은 아니지만(기기 변경 시 우회 가능), 같은 브라우저에서의
    # 반복 제출은 (campaign_id, client_fingerprint) unique 제약으로 걸러진다.
    client_fingerprint = Column(String(128))
    submitted_at = Column(DateTime, default=_now)

    campaign = relationship("SurveyCampaign", back_populates="responses")


class AcademyMonthlyMetric(Base):
    """학원이 CSV로 업로드하는 월간 운영 지표."""

    __tablename__ = "academy_monthly_metrics"
    __table_args__ = (UniqueConstraint("academy_id", "month", name="uq_academy_month"),)

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), index=True)
    month = Column(String(7))  # "YYYY-MM"
    total_students = Column(Integer, nullable=True)
    new_enrollments = Column(Integer, nullable=True)
    withdrawals = Column(Integer, nullable=True)
    renewal_eligible = Column(Integer, nullable=True)
    renewal_actual = Column(Integer, nullable=True)
    consultation_count = Column(Integer, nullable=True)
    conversion_count = Column(Integer, nullable=True)
    attendance_rate = Column(Float, nullable=True)  # 0~100
    homework_rate = Column(Float, nullable=True)  # 0~100
    created_at = Column(DateTime, default=_now)

    academy = relationship("Academy", back_populates="metrics")


class ReputationScore(Base):
    """평판 점수 계산 결과 1회분. 이력은 row를 계속 추가해 시간순으로 조회한다."""

    __tablename__ = "reputation_scores"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), index=True)
    computed_at = Column(DateTime, default=_now)
    overall_score = Column(Float)
    category_scores = Column(JSON)  # {"학부모설문": 82.0, "학생행동": 74.5, ...}
    confidence_score = Column(Float)  # 0~100
    sample_size = Column(Integer)  # 이번 계산에 사용된 설문 응답 수
    ai_summary = Column(Text, nullable=True)

    academy = relationship("Academy", back_populates="scores")


class AcademyMention(Base):
    """SNS 공개 게시물 언급 1건 (RawRecord의 SnsPostItem을 동기화·감성점수화한 결과).

    크롤링 자체는 crawler/academy_reputation_crawl.py(로컬 CLI, Scrapy)가 수행해
    RawRecord(item_type="SnsPostItem")로 적재하고, reputation_sentiment.sync_mentions()가
    academy_name이 일치하는 아직 동기화되지 않은 RawRecord만 골라 여기에 감성 점수와 함께 복사한다.
    """

    __tablename__ = "academy_mentions"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), index=True)
    platform = Column(String(32))  # naverblog / youtube / instagram / ...
    source_url = Column(String(512), unique=True, index=True)
    post_title = Column(String(500), nullable=True)
    post_body = Column(Text, nullable=True)
    published_at = Column(String(64), nullable=True)  # 원본 그대로 (플랫폼마다 형식이 달라 파싱하지 않음)
    hashtags = Column(JSON, nullable=True)
    sentiment_label = Column(Enum(SentimentLabel), default=SentimentLabel.NEUTRAL)
    sentiment_score = Column(Float)  # -1(부정) ~ 1(긍정)
    crawled_at = Column(String(64), nullable=True)
    synced_at = Column(DateTime, default=_now)

    academy = relationship("Academy", back_populates="mentions")
