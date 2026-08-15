"""교육 컨설팅 상호이해 모델 — SQLAlchemy ORM 정의 (SQLite·PostgreSQL 호환).

명세(Egonex-AI/Understand-Anything 아키텍처 교육 도메인 변환)의 핵심 엔티티:
  Persona, ActorProfile, KnowledgeNode, RelationshipEdge, UnderstandingSession,
  Insight, ActionItem, ConsultingReport, MutualUnderstandingScores, GapAnalysis, StrengthAnalysis
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, JSON, DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

# 앱 공용 Base (database.py) 를 그대로 사용 — create_all 대상에 포함되도록
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ── 1. 페르소나 ──
class Persona(Base):
    __tablename__ = "persona"
    id = Column(String, primary_key=True)  # 'student','parent','teacher'
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    knowledge_level = Column(String, default="beginner")  # beginner|intermediate|expert
    communication_style = Column(String, default="simple")  # simple|detailed|technical
    preferred_language = Column(String, default="ko")
    accessibility_needs = Column(JSON, default=list)  # ['visual','auditory','reading']
    goals = Column(JSON, default=list)
    concerns = Column(JSON, default=list)


# ── 2. 교육 관계자 프로필 ──
class ActorProfile(Base):
    __tablename__ = "actor_profile"
    id = Column(String, primary_key=True)
    persona_id = Column(String, ForeignKey("persona.id"), nullable=True)
    name = Column(String, default="")
    age = Column(Integer, nullable=True)
    grade = Column(String, nullable=True)
    subject_interests = Column(JSON, default=list)
    learning_style = Column(String, default="visual")  # visual|auditory|kinesthetic|reading
    current_understanding = Column(JSON, default=dict)  # {concepts,misconceptions,confidenceLevel}
    interaction_history = Column(JSON, default=list)
    emotional_state = Column(JSON, default=dict)  # {motivation,anxiety,engagement}
    persona = relationship("Persona", lazy="joined")


# ── 3. 상호이해 지식 그래프 노드 ──
class KnowledgeNode(Base):
    __tablename__ = "knowledge_node"
    id = Column(String, primary_key=True)
    type = Column(String, default="concept")  # concept|skill|milestone|learning_activity|assessment|emotion|relationship
    label = Column(String, nullable=False)
    description = Column(Text, default="")
    domain = Column(String, default="academic")  # academic|social|emotional|career
    difficulty = Column(Integer, default=1)  # 1-5
    prerequisites = Column(JSON, default=list)
    related_concepts = Column(JSON, default=list)
    explanations = Column(JSON, default=dict)  # {forStudent,forParent,forTeacher}
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    source = Column(String, default="ai")  # ai|teacher|student|parent|assessment
    confidence = Column(Float, default=50.0)  # 0-100


# ── 4. 관계 엣지 ──
class RelationshipEdge(Base):
    __tablename__ = "relationship_edge"
    id = Column(String, primary_key=True)
    source = Column(String, ForeignKey("knowledge_node.id"), nullable=False)
    target = Column(String, ForeignKey("knowledge_node.id"), nullable=False)
    type = Column(String, default="prerequisite")  # prerequisite|reinforces|conflicts|supports|requires|recommends
    strength = Column(Float, default=50.0)  # 0-100
    description = Column(Text, default="")
    interpretations = Column(JSON, default=dict)  # {forStudent,forParent,forTeacher}


# ── 5. 상호이해 세션 ──
class UnderstandingSession(Base):
    __tablename__ = "understanding_session"
    id = Column(String, primary_key=True)
    participants = Column(JSON, default=list)  # ActorProfile.id[]
    start_time = Column(DateTime, default=_utcnow)
    end_time = Column(DateTime, nullable=True)
    type = Column(String, default="individual")  # individual|group|parent_teacher|student_teacher|family
    agenda = Column(JSON, default=list)
    discussion_nodes = Column(JSON, default=list)
    insights = Column(JSON, default=list)  # Insight.id[]
    action_items = Column(JSON, default=list)  # ActionItem.id[]
    mutual_understanding_score = Column(JSON, default=dict)  # {studentTeacher,parentTeacher,studentParent,overall}


# ── 6. 인사이트 ──
class Insight(Base):
    __tablename__ = "insight"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    type = Column(String, default="gap")  # gap|strength|misalignment|opportunity|recommendation
    title = Column(String, default="")
    description = Column(Text, default="")
    actionable = Column(Text, default="")
    evidence = Column(JSON, default=list)
    relevant_nodes = Column(JSON, default=list)
    relevant_relationships = Column(JSON, default=list)
    delivery = Column(JSON, default=dict)  # {forStudent,forParent,forTeacher}
    priority = Column(String, default="medium")  # high|medium|low
    status = Column(String, default="draft")  # draft|validated|implemented|reviewed


# ── 7. 실행 계획 ──
class ActionItem(Base):
    __tablename__ = "action_item"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    title = Column(String, default="")
    description = Column(Text, default="")
    assigned_to = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending|in_progress|completed|blocked
    steps = Column(JSON, default=list)
    success_metrics = Column(JSON, default=list)
    progress = Column(Float, default=0.0)  # 0-100
    notes = Column(JSON, default=list)


# ── 8. 컨설팅 리포트 ──
class ConsultingReport(Base):
    __tablename__ = "consulting_report"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    generated_at = Column(DateTime, default=_utcnow)
    title = Column(String, default="")
    summary = Column(Text, default="")
    sections = Column(JSON, default=list)
    versions = Column(JSON, default=dict)  # {forStudent,forParent,forTeacher}
    attachments = Column(JSON, default=list)
    next_steps = Column(JSON, default=list)
    permissions = Column(JSON, default=dict)  # {student,parent,teacher}


# ── 9. 상호이해 점수 ──
class MutualUnderstandingScores(Base):
    __tablename__ = "mutual_understanding_scores"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    understanding = Column(JSON, default=dict)  # 6방향 이해도
    empathy = Column(JSON, default=dict)  # 6방향 공감도
    communication = Column(JSON, default=dict)  # 3쌍 의사소통
    overall = Column(Float, default=0.0)


# ── 10. 갭 분석 ──
class GapAnalysis(Base):
    __tablename__ = "gap_analysis"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    type = Column(String, default="knowledge_gap")  # knowledge_gap|expectation_gap|communication_gap|emotional_gap
    description = Column(Text, default="")
    severity = Column(Integer, default=1)  # 1-3
    related_actors = Column(JSON, default=list)
    related_concepts = Column(JSON, default=list)
    root_causes = Column(JSON, default=list)
    recommended_actions = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)


# ── 11. 강점 분석 ──
class StrengthAnalysis(Base):
    __tablename__ = "strength_analysis"
    id = Column(String, primary_key=True)
    type = Column(String, default="shared_understanding")  # shared_understanding|effective_communication|strong_relationship|mutual_trust
    description = Column(Text, default="")
    related_actors = Column(JSON, default=list)
    reinforcement_actions = Column(JSON, default=list)


__all__ = [
    "Base", "Persona", "ActorProfile", "KnowledgeNode", "RelationshipEdge",
    "UnderstandingSession", "Insight", "ActionItem", "ConsultingReport",
    "MutualUnderstandingScores", "GapAnalysis", "StrengthAnalysis",
]
