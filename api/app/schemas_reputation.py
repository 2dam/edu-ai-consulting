"""학원 평판 인텔리전스 모듈의 Pydantic 스키마. 기존 app.schemas의 flat 스타일을 따른다."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceTypeLit = Literal["homepage", "blog", "map_review", "news", "other"]
RespondentTypeLit = Literal["parent", "student"]


# ---- 학원 ----
class AcademyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region: str | None = None
    subjects: str | None = None
    academy_type: str | None = None
    target_grades: str | None = None
    edu_office_reg_no: str | None = None


class AcademyOut(BaseModel):
    id: int
    external_id: str
    name: str
    region: str | None = None
    subjects: str | None = None
    academy_type: str | None = None
    target_grades: str | None = None
    edu_office_reg_no: str | None = None
    created_at: datetime


# ---- 소스 URL ----
class AcademySourceCreate(BaseModel):
    source_type: SourceTypeLit = "other"
    url: str = Field(min_length=1, max_length=512)


class AcademySourceOut(BaseModel):
    id: int
    source_type: SourceTypeLit
    url: str
    created_at: datetime


# ---- 설문 캠페인 ----
class SurveyCampaignCreate(BaseModel):
    title: str = Field(default="학부모·학생 만족도 조사", max_length=200)
    closes_at: datetime | None = None


class SurveyCampaignOut(BaseModel):
    id: int
    academy_id: int
    token: str
    title: str
    is_active: bool
    created_at: datetime
    closes_at: datetime | None = None
    survey_url: str


# ---- 공개: 설문 질문/응답 ----
class SurveyQuestionsOut(BaseModel):
    academy_name: str
    campaign_title: str
    is_active: bool


class SurveyAnswers(BaseModel):
    class_satisfaction: int = Field(ge=1, le=5)
    teacher_satisfaction: int = Field(ge=1, le=5)
    homework_mgmt: int = Field(ge=1, le=5)
    counseling_satisfaction: int = Field(ge=1, le=5)
    improvement_felt: int = Field(ge=1, le=5)
    price_satisfaction: int = Field(ge=1, le=5)
    nps: int = Field(ge=0, le=10)
    renewal_intent: bool
    free_text: str | None = None


class SurveyResponseSubmit(BaseModel):
    respondent_type: RespondentTypeLit
    answers: SurveyAnswers
    client_fingerprint: str = Field(min_length=1, max_length=128)


class SurveyResponseOut(BaseModel):
    id: int
    submitted_at: datetime


# ---- 월간 지표 업로드 ----
class MetricsUploadResult(BaseModel):
    imported: int
    updated: int
    errors: list[str]


class AcademyMonthlyMetricOut(BaseModel):
    month: str
    total_students: int | None = None
    new_enrollments: int | None = None
    withdrawals: int | None = None
    renewal_eligible: int | None = None
    renewal_actual: int | None = None
    consultation_count: int | None = None
    conversion_count: int | None = None
    attendance_rate: float | None = None
    homework_rate: float | None = None


# ---- 평판 점수 ----
class ReputationScoreOut(BaseModel):
    id: int
    computed_at: datetime
    overall_score: float
    category_scores: dict[str, float]
    confidence_score: float
    sample_size: int
    ai_summary: str | None = None


class ReputationDashboardOut(BaseModel):
    academy: AcademyOut
    latest_score: ReputationScoreOut | None = None
    score_history: list[ReputationScoreOut]
    top_comments: list[str]


# ---- 2단계: SNS 언급 ----
class CrawlTargetsOut(BaseModel):
    academy_name: str
    region: str | None = None
    sns_urls: list[str]


class MentionSyncResult(BaseModel):
    synced: int


class AcademyMentionOut(BaseModel):
    id: int
    platform: str
    source_url: str
    post_title: str | None = None
    post_body: str | None = None
    published_at: str | None = None
    hashtags: list[str] | None = None
    sentiment_label: str
    sentiment_score: float
    synced_at: datetime


# ---- 2단계: 경쟁 학원 비교 ----
class BenchmarkGroupOut(BaseModel):
    available: bool
    label: str | None = None
    average: float | None = None
    sample_size: int | None = None
    reason: str | None = None


class BenchmarkOut(BaseModel):
    available: bool
    reason: str | None = None
    our_score: float | None = None
    region: BenchmarkGroupOut | None = None
    subject: BenchmarkGroupOut | None = None
    size_tier: BenchmarkGroupOut | None = None
    top20pct: BenchmarkGroupOut | None = None


# ---- 2단계: 평판 예측 ----
class ForecastKeyDriver(BaseModel):
    category: str
    delta: float


class ForecastOut(BaseModel):
    available: bool
    reason: str | None = None
    current_score: float | None = None
    projected_score: float | None = None
    projected_date: str | None = None
    trend_direction: str | None = None
    key_driver: ForecastKeyDriver | None = None
    at_risk_student_estimate: int | None = None
