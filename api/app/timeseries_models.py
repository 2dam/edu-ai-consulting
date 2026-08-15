"""시계열 성적·행동 예측 시스템 — 데이터 모델 (SQLAlchemy ORM).

명세의 2. 데이터 모델 설계를 실제 스키마로 옮김.
SQLite·PostgreSQL 모두 호환(Generic 타입 사용).
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TSStudent(Base):
    __tablename__ = "ts_students"
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    grade = Column(Integer)
    class_name = Column(String(40))

    scores = relationship("TSScore", back_populates="student")
    behaviors = relationship("TSBehavior", back_populates="student")


class TSSubject(Base):
    __tablename__ = "ts_subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String(40))            # 수학, 영어, 과학 ...
    category = Column(String(20))         # 인문, 자연, 예체능


class TSExam(Base):
    __tablename__ = "ts_exams"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("ts_subjects.id"))
    exam_date = Column(DateTime)
    difficulty_level = Column(Float)      # 1.0 ~ 5.0 (난이도)
    term = Column(String(20))             # 중간, 기말, 모의고사
    year = Column(Integer)

    subject = relationship("TSSubject")
    scores = relationship("TSScore", back_populates="exam")


class TSScore(Base):
    __tablename__ = "ts_scores"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("ts_students.id"))
    exam_id = Column(Integer, ForeignKey("ts_exams.id"))
    score = Column(Float)
    percentile = Column(Float)            # 백분위
    rank = Column(Integer)

    student = relationship("TSStudent", back_populates="scores")
    exam = relationship("TSExam", back_populates="scores")


class TSBehavior(Base):
    __tablename__ = "ts_behaviors"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("ts_students.id"))
    date = Column(DateTime)
    attendance = Column(Float)            # 출석률
    homework_completion = Column(Float)   # 과제 제출률
    class_participation = Column(Float)   # 수업 참여도
    study_time = Column(Float)            # 학습 시간
    sleep_hours = Column(Float)           # 수면 시간

    student = relationship("TSStudent", back_populates="behaviors")


# 과목명 → 카테고리 매핑 (명세 4. SubjectPerformanceAnalyzer)
SUBJECT_CATEGORY_MAP = {
    "math": ["수학", "미적분", "통계"],
    "science": ["물리", "화학", "생물"],
    "language": ["국어", "영어"],
    "humanities": ["역사", "지리", "윤리"],
}

# 난이도 → 설명
DIFFICULTY_LABEL = {1: "쉬운 시험", 2: "다소 쉬움", 3: "중간 난이도", 4: "어려움", 5: "매우 어려움"}
