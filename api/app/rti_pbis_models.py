"""RTI · PBIS 통합 시스템 — 데이터 모델 (SQLAlchemy ORM).

MTSS(Multi-Tiered System of Supports) 관점에서 학업(RTI)과 행동(PBIS)을
하나의 통합 저장소에서 관리한다. SQLite / PostgreSQL 모두 호환되도록
Generic SQLAlchemy 타입을 사용한다.

시계열 진도 데이터는 본 모델에서는 관계형 테이블(timestamp 컬럼)로 두며,
확장 시 InfluxDB 같은 전용 TSDB로 분리할 수 있다 (아키텍처 문서 참조).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── 1. 학생 기본 정보 (Student Core) ────────────────────────────────────────────

class Student(Base):
    __tablename__ = "rti_student"

    student_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    school_id: Mapped[str | None] = mapped_column(String(64))
    grade_level: Mapped[int | None] = mapped_column(Integer)
    classroom: Mapped[str | None] = mapped_column(String(32))
    demographics: Mapped[str | None] = mapped_column(String(256))  # 성별, 연령 등
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    screenings: Mapped[list["UniversalScreening"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    interventions: Mapped[list["Intervention"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    academic_pms: Mapped[list["ProgressMonitoringAcademic"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    behavior_pms: Mapped[list["ProgressMonitoringBehavior"]] = relationship(back_populates="student", cascade="all, delete-orphan")


# ── 2. 보편적 스크리닝 데이터 (Universal Screening) ────────────────────────────

class UniversalScreening(Base):
    __tablename__ = "rti_screening"
    __table_args__ = (UniqueConstraint("student_id", "screening_date", name="uq_screening_student_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("rti_student.student_id"))

    screening_date: Mapped[date] = mapped_column(Date, default=lambda: date.today())

    # 학업 영역 — 표준화 검사
    reading_benchmark_score: Mapped[float | None] = mapped_column(Float)   # 읽기 벤치마크
    math_percentile_rank: Mapped[float | None] = mapped_column(Float)     # 수학 백분위

    # 행동 영역 — 사회정서적 행동
    social_skills_rating: Mapped[float | None] = mapped_column(Float)      # 사회성 기술 평가(높을수록 양호)
    behavioral_risk_index: Mapped[float | None] = mapped_column(Float)    # 행동 위험 지수(높을수록 위험)

    student: Mapped["Student"] = relationship(back_populates="screenings")


# ── 3. 진도 모니터링 데이터 (Progress Monitoring) ──────────────────────────────

class ProgressMonitoringAcademic(Base):
    __tablename__ = "rti_pm_academic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("rti_student.student_id"))
    intervention_id: Mapped[int | None] = mapped_column(ForeignKey("rti_intervention.id"))
    date: Mapped[date] = mapped_column(Date, default=lambda: date.today())
    curriculum_based_measurement_score: Mapped[float] = mapped_column(Float)  # CBM 주간/격주 점수
    note: Mapped[str | None] = mapped_column(String(256))

    student: Mapped["Student"] = relationship(back_populates="academic_pms")
    intervention: Mapped["Intervention | None"] = relationship(back_populates="academic_pms")


class ProgressMonitoringBehavior(Base):
    __tablename__ = "rti_pm_behavior"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("rti_student.student_id"))
    intervention_id: Mapped[int | None] = mapped_column(ForeignKey("rti_intervention.id"))
    date: Mapped[date] = mapped_column(Date, default=lambda: date.today())
    daily_behavior_rating: Mapped[float | None] = mapped_column(Float)  # 일일 행동 평가(0~100)
    cico_points_earned: Mapped[float | None] = mapped_column(Float)     # 체크인/체크아웃 획득점
    note: Mapped[str | None] = mapped_column(String(256))

    student: Mapped["Student"] = relationship(back_populates="behavior_pms")
    intervention: Mapped["Intervention | None"] = relationship(back_populates="behavior_pms")


# ── 4. 중재 정보 (Intervention) ────────────────────────────────────────────────

class Intervention(Base):
    __tablename__ = "rti_intervention"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intervention_id: Mapped[str] = mapped_column(String(64))  # Tier2_Reading_Group, CICO, Social_Skills_Group 등
    student_id: Mapped[str] = mapped_column(ForeignKey("rti_student.student_id"))
    tier: Mapped[int] = mapped_column(Integer, default=1)     # 1, 2, 3
    assigned_date: Mapped[date | None] = mapped_column(Date)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="진행 중")  # 진행 중 / 완료 / 중단
    delivery_details: Mapped[str | None] = mapped_column(Text)  # 제공자, 장소, 시간, 빈도
    fba_hypothesis: Mapped[str | None] = mapped_column(Text)    # 기능평가 가설 (행동 중재 시)

    student: Mapped["Student"] = relationship(back_populates="interventions")
    academic_pms: Mapped[list["ProgressMonitoringAcademic"]] = relationship(back_populates="intervention")
    behavior_pms: Mapped[list["ProgressMonitoringBehavior"]] = relationship(back_populates="intervention")
    fidelity: Mapped[list["FidelityRecord"]] = relationship(back_populates="intervention", cascade="all, delete-orphan")


# ── 5. 충실도 측정 데이터 (Fidelity of Implementation) ──────────────────────────

class FidelityRecord(Base):
    __tablename__ = "rti_fidelity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intervention_id: Mapped[int] = mapped_column(ForeignKey("rti_intervention.id"))
    observer: Mapped[str | None] = mapped_column(String(64))
    date: Mapped[date] = mapped_column(Date, default=lambda: date.today())
    fidelity_score: Mapped[float] = mapped_column(Float)  # 0~100, 계획대로 실행되었는지

    intervention: Mapped["Intervention"] = relationship(back_populates="fidelity")
