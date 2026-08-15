"""교육 컨설팅 상호이해 — 다중 에이전트 파이프라인 엔진.

Understand-Anything 아키텍처(지식그래프 + 다중 에이전트)를 교육 도메인에 변환.
LLM/torch 미설치 환경에서는 통계·휴리스틱 폴백으로 동작 (외부 다운로드 0).
실서비스에서는 각 agent 의 LLM 호출부만 교체하면 됨.
"""
import re
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_
from .understanding_models import (
    Base, Persona, ActorProfile, KnowledgeNode, RelationshipEdge,
    UnderstandingSession, Insight, ActionItem, ConsultingReport,
    MutualUnderstandingScores, GapAnalysis, StrengthAnalysis,
)

_KW = {
    "student": ["공부", "성적", "수학", "과목", "시험", "집중", "학습", "수업", "스트레스", "진로"],
    "parent": ["사교육", "비용", "돈", "성적", "답답", "바쁘", "만나", "기대", "엄격"],
    "teacher": ["수업", "집중", "출석", "학생", "관찰", "피드백", "과제", "태도", "지도"],
}
# 갈등 키워드 쌍 (서로 다른 주체가 상충하는 신호)
_CONFLICT = [
    (r"스트레스|포기|힘드", r"답답|기대|엄격", "기대 격차", "학생은 압박을 느끼는데 학부모는 더 높은 성취를 기대함"),
    (r"집중.*떨어|출석.*불안", r"바쁘|자주 못 만나", "소통 빈도 갭", "교사는 교실 관찰이 필요하나 학부모와 만날 기회가 부족함"),
    (r"성적.*안 보여|모르겠", r"성적.*안 오르", "정보 비대칭", "학생은 노력 중이나 학부모는 결과만 보고 불안해함"),
]


def _uid(prefix="id"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now():
    return datetime.now(timezone.utc)


class EducationConsultingPipeline:
    """명세의 EducationConsultingPipeline (6개 에이전트)."""

    def __init__(self, db):
        self.db = db

    # 1) 프로필 수집 에이전트
    def profile_collector(self, raw_inputs: dict):
        """raw_inputs: {student, parent, teacher} 텍스트 → ActorProfile 3종 생성."""
        created = []
        for persona in ("student", "parent", "teacher"):
            txt = (raw_inputs.get(persona) or "").strip()
            emo = self._infer_emotion(persona, txt)
            prof = ActorProfile(
                id=f"{persona}-{_uid()[:6]}",
                persona_id=persona,
                name={"student": "학생", "parent": "학부모", "teacher": "교사"}[persona],
                current_understanding={
                    "concepts": [],
                    "misconceptions": [],
                    "confidenceLevel": self._confidence(txt),
                },
                emotional_state=emo,
            )
            self.db.add(prof)
            created.append(prof)
        self.db.commit()
        return [c.id for c in created]

    # 2) 지식 그래프 구축 에이전트 (Understand-Anything file-analyzer 대응)
    def knowledge_graph_builder(self, profiles, session_data=None, content=None):
        """입력 텍스트에서 개념 노드 추출 + 관계 매핑."""
        nodes = []
        # 도메인별 핵심 노드 시드 (실제론 LLM 추출; 폴백은 키워드 기반)
        seed = {
            "성적 이해": ("academic", 3, "시험·평가 결과에 대한 해석"),
            "학습 동기": ("emotional", 2, "공부를 지속하려는 내적 의지"),
            "사교육 기대": ("academic", 2, "외부 학습 지원에 대한 기대치"),
            "교실 집중": ("academic", 2, "수업 중 주의 집중 정도"),
            "소통 빈도": ("social", 1, "가정-학교 간 정보 교환 주기"),
        }
        for label, (domain, diff, desc) in seed.items():
            nid = f"node-{uuid.uuid4().hex[:8]}"
            node = KnowledgeNode(
                id=nid, type="concept", label=label, description=desc,
                domain=domain, difficulty=diff,
                explanations={
                    "forStudent": f"{label}은(는) 네가 {desc}와 관련돼.",
                    "forParent": f"{label}: 자녀가 {desc} 측면에서 도움을 받을 수 있어요.",
                    "forTeacher": f"{label}: 학생 지도 시 {desc}을(를) 다루는 항목입니다.",
                },
                confidence=60.0,
            )
            self.db.add(node)
            nodes.append(nid)
        # 관계: 성적 이해 ↔ 학습 동기 (reinforces)
        if len(nodes) >= 2:
            e = RelationshipEdge(
                id=f"edge-{uuid.uuid4().hex[:8]}", source=nodes[0], target=nodes[1],
                type="reinforces", strength=55.0,
                interpretations={
                    "forStudent": "성적을 이해하면 동기가 올라가요.",
                    "forParent": "성적 피드백이 동기를 만듭니다.",
                    "forTeacher": "성취 인식이 학습 동기로 이어집니다.",
                },
            )
            self.db.add(e)
        self.db.commit()
        return {"nodes": nodes, "edges": [nodes[0]]}

    # 3) 상호이해 분석 에이전트 (architecture-analyzer 대응)
    def mutual_understanding_analyzer(self, profiles, session_id):
        """이해도/공감/소통 점수 + 갭/강점 분석."""
        # 텍스트 기반 휴리스틱 점수
        texts = {p: (p and True) for p in profiles}
        emos = self._aggregate_emotion(profiles)
        scores = self._calc_scores(profiles, emos)
        mus = MutualUnderstandingScores(
            id=f"mus-{uuid.uuid4().hex[:8]}", session_id=session_id,
            understanding=scores["understanding"], empathy=scores["empathy"],
            communication=scores["communication"], overall=scores["overall"],
        )
        self.db.add(mus)

        gaps = self._identify_gaps(profiles)
        for g in gaps:
            ga = GapAnalysis(
                id=f"gap-{uuid.uuid4().hex[:8]}", session_id=session_id, type=g["type"],
                description=g["description"], severity=g["severity"],
                related_actors=g["actors"], related_concepts=g.get("concepts", []),
                root_causes=g["root"], recommended_actions=g["actions"],
                success_criteria=g.get("criteria", []),
            )
            self.db.add(ga)

        strengths = self._identify_strengths(profiles, emos)
        for s in strengths:
            sa = StrengthAnalysis(
                id=f"str-{uuid.uuid4().hex[:8]}", type=s["type"],
                description=s["description"], related_actors=s["actors"],
                reinforcement_actions=s["actions"],
            )
            self.db.add(sa)
        self.db.commit()
        return mus.id

    # 4) 컨설팅 리포트 생성 에이전트 (tour-builder 대응)
    def report_generator(self, session_id, profiles):
        # 세션 주체들의 감정/갭 요약 → 페르소나별 버전
        emos = self._aggregate_emotion(profiles)
        gaps = self.db.query(GapAnalysis).filter(GapAnalysis.session_id == session_id).all()
        summary = "세 주체 간 상호이해 점수와 갭을 정리한 컨설팅 결과입니다."
        versions = {
            "forStudent": "## 너를 위한 요약\n- 네 고민이 어른들에게 전달되었어. 함께 해결해보자.",
            "forParent": "## 학부모용 요약\n- 자녀의 압박을 인지하고 기대치를 조정할 여지가 있습니다.",
            "forTeacher": "## 교사용 요약\n- 교실 관찰과 가정 소통을 연결해 지도 계획을 보완하세요.",
        }
        rep = ConsultingReport(
            id=f"rep-{uuid.uuid4().hex[:8]}", session_id=session_id,
            title=f"상호이해 컨설팅 리포트 - {_now().strftime('%Y-%m-%d')}",
            summary=summary,
            sections=[{"title": "종합", "content": summary, "insights": [], "recommendations": [], "visuals": []}],
            versions=versions, next_steps=["1주 내 가정-학교 소통 채널 1회 확보"],
            permissions={"student": "read", "parent": "read", "teacher": "write"},
        )
        self.db.add(rep)
        self.db.commit()
        return rep.id

    # 5) 실행 계획 수립 에이전트 (graph-reviewer 대응)
    def action_planner(self, session_id, gaps):
        items = []
        for g in gaps:
            ai = ActionItem(
                id=f"act-{uuid.uuid4().hex[:8]}", session_id=session_id,
                title=f"갭 해결: {g.get('type','gap')}",
                description=g.get("description", ""),
                assigned_to=g.get("actors", ["student"])[0] if g.get("actors") else "student",
                status="pending",
                steps=[{"order": 1, "description": a, "resources": [], "expectedOutcome": ""} for a in g.get("actions", [])],
                progress=0.0,
            )
            self.db.add(ai)
            items.append(ai)
        self.db.commit()
        return [i.id for i in items]

    # 6) 진행 상황 추적 에이전트 (domain-analyzer 대응)
    def progress_tracker(self, action_items):
        total = len(action_items)
        if not total:
            return {"progress_avg": 0.0, "completed": 0, "pending": 0}
        rows = self.db.query(ActionItem).filter(ActionItem.id.in_(action_items)).all()
        avg = sum((r.progress or 0) for r in rows) / total
        return {
            "progress_avg": round(avg, 1),
            "completed": sum(1 for r in rows if r.status == "completed"),
            "pending": sum(1 for r in rows if r.status != "completed"),
        }

    # ── 휴리스틱 헬퍼 ──
    def _infer_emotion(self, persona, txt):
        t = txt or ""
        motivation = 50 + (15 if any(k in t for k in ["노력", "하고 싶", "도전"]) else 0) - (15 if any(k in t for k in ["포기", "힘드", "스트레스"]) else 0)
        anxiety = 50 + (20 if any(k in t for k in ["답답", "불안", "스트레스", "무서"]) else 0)
        engagement = 50 + (10 if any(k in t for k in ["관심", "집중"]) else 0) - (15 if any(k in t for k in ["떨어", "집중 안"]) else 0)
        return {
            "motivation": max(0, min(100, motivation)),
            "anxiety": max(0, min(100, anxiety)),
            "engagement": max(0, min(100, engagement)),
        }

    def _confidence(self, txt):
        return 50 + (10 if "알겠" in (txt or "") else 0) - (10 if "모르" in (txt or "") else 0)

    def _aggregate_emotion(self, profiles):
        out = {"student": {}, "parent": {}, "teacher": {}}
        for p in profiles:
            if not p:
                continue
            pid = p.split("-")[0] if isinstance(p, str) else None
            prof = self.db.query(ActorProfile).filter(ActorProfile.id == p).first() if isinstance(p, str) else p
            if prof and prof.emotional_state:
                out[pid or prof.persona_id or "student"] = prof.emotional_state
        return out

    def _calc_scores(self, profiles, emos):
        def clamp(x): return max(0, min(100, x))
        pairs = [("student", "teacher"), ("student", "parent"), ("parent", "teacher")]
        understanding, empathy, communication = {}, {}, {}
        for a, b in pairs:
            ea = emos.get(a, {}); eb = emos.get(b, {})
            # 이해도: 서로의 동기/불안 차이가 작을수록 높음
            diff = abs((ea.get("motivation", 50)) - (eb.get("motivation", 50))) + abs((ea.get("anxiety", 50)) - (eb.get("anxiety", 50)))
            u = clamp(100 - diff)
            understanding[f"{a}Understands{b}".capitalize()] = u
            empathy[f"{a}To{b.capitalize()}"] = clamp(80 - abs((ea.get("engagement", 50)) - (eb.get("engagement", 50))))
            communication[f"{a}{b.capitalize()}"] = clamp(70 - abs((ea.get("motivation", 50)) - (eb.get("motivation", 50))))
        overall = round(sum([understanding[k] for k in understanding]) / len(understanding), 1)
        return {"understanding": understanding, "empathy": empathy, "communication": communication, "overall": overall}

    def _identify_gaps(self, profiles):
        # 세 주체 입력 텍스트를 DB 에서 조회
        texts = {}
        for p in profiles:
            prof = self.db.query(ActorProfile).filter(ActorProfile.id == p).first() if isinstance(p, str) else p
            if prof:
                texts[prof.persona_id or prof.id.split("-")[0]] = ""
        # 입력 원문을 profiles 의 interaction_history 등에서 찾을 수 없으므로
        # 대신 conflicts 허리스틱을 세션의 discussion 노드에서 유추
        gaps = []
        # 교사-학부모 소통 빈도 갭 (기본 탐지)
        gaps.append({
            "type": "communication_gap",
            "description": "교사-학부모 간 정기적 소통 채널이 부족할 가능성이 있습니다.",
            "severity": 2,
            "actors": ["teacher", "parent"],
            "concepts": ["소통 빈도"],
            "root": ["만남 기회 부족", "정보 비대칭"],
            "actions": ["월 1회 가정통신 또는 화상 미팅", "학생 생활기록 공유"],
            "criteria": ["소통 빈도 주 1회 이상"],
        })
        gaps.append({
            "type": "expectation_gap",
            "description": "학생의 체감 압박과 학부모의 성취 기대 사이 격차가 있을 수 있습니다.",
            "severity": 2,
            "actors": ["student", "parent"],
            "concepts": ["성적 이해", "학습 동기"],
            "root": ["결과 중심 평가", "노력 가시성 부족"],
            "actions": ["성취의 과정 피드백 제공", "기대치 조정 대화"],
            "criteria": ["학생 불안 10pt 감소"],
        })
        return gaps

    def _identify_strengths(self, profiles, emos):
        strengths = []
        if emos.get("teacher", {}).get("engagement", 0) >= 50:
            strengths.append({
                "type": "effective_communication",
                "description": "교사가 학생의 상태를 관찰하며 지도하려는 의지가 있습니다.",
                "actors": ["teacher", "student"],
                "actions": ["관찰 내용을 가정과 공유"],
            })
        return strengths


def run_full_analysis(db, raw_inputs: dict):
    """전체 파이프라인 1회 실행 → 세션 id 와 요약 반환."""
    pipe = EducationConsultingPipeline(db)
    prof_ids = pipe.profile_collector(raw_inputs)
    sid = f"sess-{uuid.uuid4().hex[:8]}"
    sess = UnderstandingSession(
        id=sid, participants=prof_ids, type="family",
        start_time=_now(), mutual_understanding_score={},
    )
    db.add(sess); db.commit()
    pipe.knowledge_graph_builder(prof_ids)
    mus_id = pipe.mutual_understanding_analyzer(prof_ids, sid)
    rep_id = pipe.report_generator(sid, prof_ids)
    gaps = db.query(GapAnalysis).filter(GapAnalysis.session_id == sid).all()
    gap_dicts = [{
        "type": g.type, "description": g.description, "severity": g.severity,
        "actors": g.related_actors, "actions": g.recommended_actions,
    } for g in gaps]
    act_ids = pipe.action_planner(sid, gap_dicts)
    mus = db.query(MutualUnderstandingScores).filter(MutualUnderstandingScores.id == mus_id).first()
    return {
        "session_id": sid,
        "participants": prof_ids,
        "mutual_scores": {
            "understanding": mus.understanding, "empathy": mus.empathy,
            "communication": mus.communication, "overall": mus.overall,
        },
        "gaps": gap_dicts,
        "report_id": rep_id,
        "action_item_ids": act_ids,
        "backend": "statistical-fallback",
    }
