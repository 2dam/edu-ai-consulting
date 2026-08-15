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
    session_id = Column(String, nullable=True)
    type = Column(String, default="shared_understanding")  # shared_understanding|effective_communication|strong_relationship|mutual_trust
    description = Column(Text, default="")
    related_actors = Column(JSON, default=list)
    reinforcement_actions = Column(JSON, default=list)


__all__ = [
    "Base", "Persona", "ActorProfile", "KnowledgeNode", "RelationshipEdge",
    "UnderstandingSession", "Insight", "ActionItem", "ConsultingReport",
    "MutualUnderstandingScores", "GapAnalysis", "StrengthAnalysis",
]


def migrate_understanding_columns(engine):
    """SQLite 영구 디스크에 구버전 이해모델 테이블이 남아있을 때 스키마를 최신화한다(멱등).

    SQLAlchemy create_all 는 기존 테이블을 건드리지 않으므로, Render 재배포 시
    understanding_* 테이블에 새 컬럼이 없어 500이 나는 것을 방지.
    - 누락 컬럼이 없으면 그대로 둔다(기존 행 보존).
    - 누락 컬럼이 하나라도 있으면 해당 이해모델 테이블만 DROP 후 recreate 한다.
      (이해모델 테이블의 기존 행은 데모/샘플 데이터라 손실해도 무방; 크롤링
      운영 데이터(raw_records 등 타 테이블)는 절대 건드리지 않는다.)
    - PostgreSQL/신규 DB에서는 테이블이 create_all 로 이미 최신이므로 무해.
    """
    try:
        from sqlalchemy import inspect, text
    except Exception:
        return
    insp = inspect(engine)
    if not insp or not getattr(insp, "dialect", None) or insp.dialect.name != "sqlite":
        return
    # 이해모델 테이블 → 모델에 정의된 전체 컬럼명
    expected = {
        "persona": {"id", "name", "description", "knowledge_level", "communication_style",
                    "preferred_language", "accessibility_needs", "goals", "concerns"},
        "actor_profile": {"id", "persona_id", "name", "age", "grade", "subject_interests",
                          "learning_style", "current_understanding", "emotional_state", "interaction_history"},
        "knowledge_node": {"id", "type", "label", "description", "domain", "difficulty",
                           "prerequisites", "related_concepts", "explanations", "created_at",
                           "updated_at", "source", "confidence"},
        "relationship_edge": {"id", "source", "target", "type", "strength", "description", "interpretations"},
        "understanding_session": {"id", "participants", "start_time", "end_time", "type",
                                  "agenda", "discussion_nodes", "insights", "action_items", "mutual_understanding_score"},
        "insight": {"id", "session_id", "type", "title", "description", "actionable", "evidence",
                    "relevant_nodes", "relevant_relationships", "delivery", "priority", "status"},
        "action_item": {"id", "session_id", "title", "description", "assigned_to", "due_date",
                        "status", "steps", "success_metrics", "progress", "notes"},
        "consulting_report": {"id", "session_id", "generated_at", "title", "summary", "sections",
                              "versions", "attachments", "next_steps", "permissions"},
        "mutual_understanding_scores": {"id", "session_id", "understanding", "empathy", "communication", "overall"},
        "gap_analysis": {"id", "session_id", "type", "description", "severity", "related_actors",
                         "related_concepts", "root_causes", "recommended_actions", "success_criteria"},
        "strength_analysis": {"id", "session_id", "type", "description", "related_actors", "reinforcement_actions"},
    }
    with engine.connect() as conn:
        for tbl, cols in expected.items():
            if not insp.has_table(tbl):
                continue
            existing = {c["name"] for c in insp.get_columns(tbl)}
            if cols.issubset(existing):
                continue  # 최신 — 그대로
            # 누락 컬럼 있음 → 이해모델 테이블만 안전하게 재생성
            try:
                conn.execute(text(f'DROP TABLE "{tbl}"'))
                conn.commit()
            except Exception:
                conn.rollback()
    # 누락 테이블/재생성분은 create_all 이 메워준다
    Base.metadata.create_all(bind=engine)
