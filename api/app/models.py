from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String, Text

from app.database import Base


class RawRecord(Base):
    """크롤러가 수집한 원시 데이터 (사업계획서 3.1항 5개 유형 공통 저장소).

    item_type으로 필터한 뒤 created_at으로 정렬하는 조회(/education-facilities 등)가
    시설 데이터 수천~만 건 규모에서 수 초~수십 초까지 걸려 타임아웃/502로 이어지는
    문제가 있었다 — item_type 단일 인덱스만으로는 정렬 단계에서 풀 소트가 필요했기
    때문. 복합 인덱스로 정렬까지 인덱스로 처리되게 한다. 기존 운영 DB에는 이 인덱스가
    자동 반영되지 않으므로(create_all은 신규 테이블만 생성) main.py의 lifespan에서
    CREATE INDEX IF NOT EXISTS로 한 번 더 보정한다.
    """

    __tablename__ = "raw_records"
    __table_args__ = (
        Index("ix_raw_records_item_type_created_at", "item_type", "created_at"),
        # facility_type/region/district는 예전엔 data(JSON) 안에서 json_extract로 걸러서
        # /education-facilities, /region-stats가 12만 건대 raw_records를 매번 풀스캔했다.
        # 실제 컬럼으로 승격해 인덱스를 태우도록 바꾼다 — 기존 운영 DB는 create_all이
        # 컬럼을 추가해주지 않으므로 main.py의 lifespan에서 ALTER TABLE + 백필로 보정한다.
        Index("ix_raw_records_item_type_facility_type_created_at", "item_type", "facility_type", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(64), index=True)
    data = Column(JSON)
    facility_type = Column(String(32), nullable=True)
    region = Column(String(64), index=True, nullable=True)
    district = Column(String(64), index=True, nullable=True)
    source_url = Column(String(512))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConsultingReport(Base):
    """AI 분석 엔진이 생성한 학생별 리포트."""

    __tablename__ = "consulting_reports"

    id = Column(Integer, primary_key=True, index=True)
    student_label = Column(String(128))
    tier = Column(String(16))
    input_summary = Column(Text)
    psych_scores = Column(JSON, nullable=True)
    student_features = Column(JSON, nullable=True)   # predictive_model 입력 피처 (루프 재학습용)
    prompt_variant = Column(String(8), nullable=True) # "A" / "B" — 어떤 프롬프트 변형이 사용됐는지
    report_text = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FeedbackRecord(Base):
    """리포트에 대한 학생·컨설턴트 피드백 — 루프 재학습의 핵심 신호."""

    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, index=True)           # ConsultingReport.id (FK 없이 느슨하게 참조)
    student_label = Column(String(128))
    rating = Column(Integer)                          # 1~5점 (5=매우 도움됨)
    comment = Column(Text, nullable=True)
    # 실제 결과 (나중에 입력 가능): "improved" / "no_change" / "worsened"
    actual_outcome = Column(String(32), nullable=True)
    processed = Column(Boolean, default=False)        # 이 피드백이 재학습 사이클에 반영됐는지
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LoopMetric(Base):
    """자가진화 루프 사이클 실행 기록 — 모델·프롬프트가 어떻게 발전했는지 추적."""

    __tablename__ = "loop_metrics"

    id = Column(Integer, primary_key=True, index=True)
    trigger = Column(String(32))                      # "feedback_threshold" / "scheduled" / "manual"
    feedbacks_used = Column(Integer, default=0)
    accuracy_before = Column(Float, nullable=True)    # 재학습 전 CV 정확도
    accuracy_after = Column(Float, nullable=True)     # 재학습 후 CV 정확도
    prompt_variant_switched = Column(Boolean, default=False)
    active_prompt_variant = Column(String(8), nullable=True)  # 이 사이클 후 활성 variant
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
