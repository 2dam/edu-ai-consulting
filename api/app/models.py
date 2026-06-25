from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from app.database import Base


class RawRecord(Base):
    """크롤러가 수집한 원시 데이터 (사업계획서 3.1항 5개 유형 공통 저장소)."""

    __tablename__ = "raw_records"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(64), index=True)  # CurriculumItem / AdmissionResultItem / PolicyNewsItem
    data = Column(JSON)
    source_url = Column(String(512))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConsultingReport(Base):
    """AI 분석 엔진이 생성한 학생별 리포트 (3.2/3.3항 'AI 분석 리포트')."""

    __tablename__ = "consulting_reports"

    id = Column(Integer, primary_key=True, index=True)
    student_label = Column(String(128))  # 비식별화된 학생 식별자 (실명 금지)
    tier = Column(String(16))  # BASIC / STANDARD / PREMIUM
    input_summary = Column(Text)
    report_text = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
