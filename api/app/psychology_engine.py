"""
Comprehensive_Educational_Consulting_Psychology_Report.pdf 에서 정리된 핵심 이론을
정량 측정 가능한 형태로 코드화한 모듈.

- 자기결정성 이론 (Deci & Ryan, SDT): 자율성/유능성/관계성 3개 하위척도
- 자기조절학습 (SRL) / 메타인지: 계획-점검-평가 3개 하위척도
- 긍정심리학: 강점 인식 + 심리적 안녕감 2개 하위척도
- 생태학적 행동지원 (PBS/생태학적 관점): 학생-환경(교실/가정) 불일치 체크리스트

표준화 심리검사 문항은 1~5점 리커트(PSY_ITEMS)로 모듈 내에 복원되어 있으며,
3소스(학생/학부모/교육기관) 응답을 가중 융합해 하위척도 점수를 산출한다.
학생 자가보고는 본인이, 학부모 보고는 관찰로, 교육기관 자료는 비교과·상담기록으로
각각 다른 문항 묶음(PSY_ITEMS_BY_SOURCE)으로 수집한다.
"""
from statistics import mean

# 각 하위척도에 속하는 문항 ID 목록. 문항 자체(설문 문구)는 프런트/앱에서 관리하고,
# 여기서는 채점에 필요한 문항-하위척도 매핑만 코드화한다.
SDT_ITEMS = {
    "autonomy": ["sdt_a1", "sdt_a2", "sdt_a3"],
    "competence": ["sdt_c1", "sdt_c2", "sdt_c3"],
    "relatedness": ["sdt_r1", "sdt_r2", "sdt_r3"],
}

SRL_ITEMS = {
    "planning": ["srl_p1", "srl_p2"],
    "monitoring": ["srl_m1", "srl_m2"],
    "evaluation": ["srl_e1", "srl_e2"],
}

POSITIVE_PSYCH_ITEMS = {
    "strengths_awareness": ["pp_s1", "pp_s2"],
    "wellbeing": ["pp_w1", "pp_w2"],
}

# 생태학적 관점: 학생 개인 결함이 아니라 환경(교실/가정)과의 불일치를 점검.
# 점수가 높을수록 환경과의 불일치(스트레스 요인)가 큼 — 역방향 해석.
ECOLOGICAL_ITEMS = {
    "classroom_fit": ["eco_cl1", "eco_cl2"],
    "home_support": ["eco_h1", "eco_h2"],
}

# ── 표준화 심리검사 문항 뱅크 (1~5 리커트, 4이론 × 11하위척도 × 4문항 = 44문항) ──
# 각 문항은 하위척도(subscale)에 매핑되며, score_assessment에서 평균을 낸다.
# dir: 1=점수 높을수록 긍정, -1=점수 높을수록 불일치/부정(생태 하위척도)
PSY_ITEMS = [
    # SDT - 자율성
    {"id": "sdt_a1", "sub": "sdt_autonomy", "dir": 1, "q": "스스로 학습 목표나 공부 방법을 고를 수 있는 느낌이 듭니다.", "src": ["student"]},
    {"id": "sdt_a2", "sub": "sdt_autonomy", "dir": 1, "q": "하고 싶은 과목이나 주제를 스스로 정할 기회가 많습니다.", "src": ["student"]},
    {"id": "sdt_a3", "sub": "sdt_autonomy", "dir": 1, "q": "부모님/선생님이 시키는 대로만 하는 것보다 내 방식으로 해보는 시간이 있습니다.", "src": ["student", "parent"]},
    {"id": "sdt_a4", "sub": "sdt_autonomy", "dir": 1, "q": "학습 계획을 세울 때 아이의 의견을 충분히 묻습니다.", "src": ["parent"]},
    # SDT - 유능성
    {"id": "sdt_c1", "sub": "sdt_competence", "dir": 1, "q": "내가 하는 학습이 잘 풀리고 있다는 확신이 있습니다.", "src": ["student"]},
    {"id": "sdt_c2", "sub": "sdt_competence", "dir": 1, "q": "어려운 문제도 방법을 찾아내면 해낼 수 있다고 믿습니다.", "src": ["student"]},
    {"id": "sdt_c3", "sub": "sdt_competence", "dir": 1, "q": "최근 스스로 해낸 일이 하나 이상 있습니다.", "src": ["student", "parent"]},
    {"id": "sdt_c4", "sub": "sdt_competence", "dir": 1, "q": "아이가 어떤 과목에서든 '나도 할 수 있다'는 태도를 보입니다.", "src": ["parent"]},
    # SDT - 관계성
    {"id": "sdt_r1", "sub": "sdt_relatedness", "dir": 1, "q": "선생님이나 친구와 마음이 통한다고 느낍니다.", "src": ["student"]},
    {"id": "sdt_r2", "sub": "sdt_relatedness", "dir": 1, "q": "학교/학원에서 도움을 요청하기 편한 사람이 있습니다.", "src": ["student"]},
    {"id": "sdt_r3", "sub": "sdt_relatedness", "dir": 1, "q": "또래 관계에서 외롭거나 소외된 느낌을 자주 받습니다(역문항).", "src": ["student", "parent"]},
    {"id": "sdt_r4", "sub": "sdt_relatedness", "dir": 1, "q": "아이가 교우 관계나 선생님과의 관계에서 안정적입니다.", "src": ["parent"]},
    # SRL - 계획
    {"id": "srl_p1", "sub": "srl_planning", "dir": 1, "q": "공부하기 전에 무엇을 언제까지 할지 구체적으로 계획합니다.", "src": ["student"]},
    {"id": "srl_p2", "sub": "srl_planning", "dir": 1, "q": "한 주 단위 학습 목표를 적어두고 따릅니다.", "src": ["student"]},
    {"id": "srl_p3", "sub": "srl_planning", "dir": 1, "q": "시험 일정을 미리 확인하고 공부를 배분합니다.", "src": ["student", "parent"]},
    {"id": "srl_p4", "sub": "srl_planning", "dir": 1, "q": "아이가 스스로 주간 학습 계획을 세웁니다.", "src": ["parent"]},
    # SRL - 점검(모니터링)
    {"id": "srl_m1", "sub": "srl_monitoring", "dir": 1, "q": "공부 중 '지금 집중되고 있는가'를 스스로 체크합니다.", "src": ["student"]},
    {"id": "srl_m2", "sub": "srl_monitoring", "dir": 1, "q": "잘 모르겠는 부분을 풀이 도중에 스스로 알아챕니다.", "src": ["student"]},
    {"id": "srl_m3", "sub": "srl_monitoring", "dir": 1, "q": "공부하다 막히면 어디서 틀렸는지 스스로 짚어봅니다.", "src": ["student", "parent"]},
    {"id": "srl_m4", "sub": "srl_monitoring", "dir": 1, "q": "아이가 혼자 공부할 때도 흐름을 스스로 점검합니다.", "src": ["parent"]},
    # SRL - 평가
    {"id": "srl_e1", "sub": "srl_evaluation", "dir": 1, "q": "시험이나 과제 후에 내 오답 원인을 스스로 정리합니다.", "src": ["student"]},
    {"id": "srl_e2", "sub": "srl_evaluation", "dir": 1, "q": "공부 방법이 효과 있었는지 돌아보고 고칩니다.", "src": ["student"]},
    {"id": "srl_e3", "sub": "srl_evaluation", "dir": 1, "q": "성적표를 받고 나만의 부족한 부분을 스스로 파악합니다.", "src": ["student", "parent"]},
    {"id": "srl_e4", "sub": "srl_evaluation", "dir": 1, "q": "아이가 결과를 보고 다음 학습을 스스로 조정합니다.", "src": ["parent"]},
    # 긍정심리 - 강점 인식
    {"id": "pp_s1", "sub": "pp_strengths", "dir": 1, "q": "내가 잘하는 것(강점)이 무엇인지 명확히 압니다.", "src": ["student"]},
    {"id": "pp_s2", "sub": "pp_strengths", "dir": 1, "q": "강점을 살릴 수 있는 활동에 자주 참여합니다.", "src": ["student", "parent"]},
    {"id": "pp_s3", "sub": "pp_strengths", "dir": 1, "q": "아이가 자신의 좋은 점을 스스로 말할 수 있습니다.", "src": ["parent"]},
    {"id": "pp_s4", "sub": "pp_strengths", "dir": 1, "q": "학교생활기록/비교과에서 두드러진 강점 영역이 보입니다.", "src": ["institution"]},
    # 긍정심리 - 안녕감
    {"id": "pp_w1", "sub": "pp_wellbeing", "dir": 1, "q": "전반적으로 학교/학습 생활에 즐거움이 있습니다.", "src": ["student"]},
    {"id": "pp_w2", "sub": "pp_wellbeing", "dir": 1, "q": "스트레스가 쌓여도 회복하는 나만의 방법이 있습니다.", "src": ["student"]},
    {"id": "pp_w3", "sub": "pp_wellbeing", "dir": 1, "q": "아이가 전반적으로 안정적이고 긍정적인 기분 상태입니다.", "src": ["parent"]},
    {"id": "pp_w4", "sub": "pp_wellbeing", "dir": 1, "q": "상담/생활기록상 정서 안정 지표가 양호합니다.", "src": ["institution"]},
    # 생태 - 교실 적합도(역방향: 점수 낮을수록 불일치 큼)
    {"id": "eco_cl1", "sub": "eco_classroom", "dir": -1, "q": "수업 방식이나 평가가 아이에게 맞지 않는 경우가 잦습니다.", "src": ["student", "parent", "institution"]},
    {"id": "eco_cl2", "sub": "eco_classroom", "dir": -1, "q": "교실 분위기나 규칙이 아이에게 부담이 됩니다.", "src": ["student", "parent", "institution"]},
    {"id": "eco_cl3", "sub": "eco_classroom", "dir": -1, "q": "학교생활기록상 교우/수업 참여 불일치 신호가 보입니다.", "src": ["institution"]},
    {"id": "eco_cl4", "sub": "eco_classroom", "dir": -1, "q": "선생님과의 관계에서 마찰이나 소통 단절이 잦습니다.", "src": ["parent", "institution"]},
    # 생태 - 가정 지원(역방향)
    {"id": "eco_h1", "sub": "eco_home", "dir": -1, "q": "집에서 공부할 공간이나 규칙이 자주 바뀌어 불안정합니다.", "src": ["student", "parent"]},
    {"id": "eco_h2", "sub": "eco_home", "dir": -1, "q": "부모님의 기대와 실제 지원 사이에 괴리가 느껴집니다.", "src": ["student", "parent"]},
    {"id": "eco_h3", "sub": "eco_home", "dir": -1, "q": "가정의 학습 지원이 아이 필요에 비해 부족하다고 판단됩니다.", "src": ["parent"]},
    {"id": "eco_h4", "sub": "eco_home", "dir": -1, "q": "학부모 상담 기록상 가정 지지 자원이 제한적입니다.", "src": ["institution"]},
]

# 3소스별 수집 문항 맵 (프론트 렌더용)
PSY_ITEMS_BY_SOURCE = {
    "student": [it for it in PSY_ITEMS if "student" in it["src"]],
    "parent": [it for it in PSY_ITEMS if "parent" in it["src"]],
    "institution": [it for it in PSY_ITEMS if "institution" in it["src"]],
}

# 하위척도 → 이론 그룹핑 (출력/해석용)
SUBSCALE_THEORY = {
    "sdt_autonomy": "self_determination", "sdt_competence": "self_determination", "sdt_relatedness": "self_determination",
    "srl_planning": "self_regulated_learning", "srl_monitoring": "self_regulated_learning", "srl_evaluation": "self_regulated_learning",
    "pp_strengths": "positive_psychology", "pp_wellbeing": "positive_psychology",
    "eco_classroom": "ecological_fit", "eco_home": "ecological_fit",
}

SOURCE_WEIGHTS = {"student": 0.40, "parent": 0.30, "institution": 0.30}

LEVEL_BANDS = [
    (1.0, 2.4, "낮음"),
    (2.4, 3.6, "보통"),
    (3.6, 5.01, "높음"),
]


def _level(score: float) -> str:
    for low, high, label in LEVEL_BANDS:
        if low <= score < high:
            return label
    return "보통"


def _subscale_scores(answers: dict[str, int], item_map: dict[str, list[str]]) -> dict[str, dict]:
    result = {}
    for subscale, item_ids in item_map.items():
        values = [answers[i] for i in item_ids if i in answers]
        if not values:
            continue
        avg = round(mean(values), 2)
        result[subscale] = {"score": avg, "level": _level(avg)}
    return result


def _fuse_subscales(scores_by_subscale: dict[str, float]) -> dict[str, dict]:
    """3소스 응답을 하위척도별로 가중 융합(미입력 소스는 가중에서 제외 후 재분배)."""
    # scores_by_subscale: {subscale: {source: value}}
    fused: dict[str, dict] = {}
    for sub, src_vals in scores_by_subscale.items():
        tw, total = 0.0, 0.0
        for src, val in src_vals.items():
            w = SOURCE_WEIGHTS.get(src, 0)
            tw += w
            total += w * val
        if tw > 0:
            avg = round(total / tw, 2)
            fused[sub] = {"score": avg, "level": _level(avg)}
    return fused


def score_assessment(answers: dict[str, int] | None = None,
                     answers_by_source: dict[str, dict[str, int]] | None = None) -> dict:
    """심리 설문 응답을 채점.

    - answers: 기존 단일 dict 방식(하위 호환)
    - answers_by_source: {student/parent/institution: {item_id: 1~5}} 3소스 방식
      → 하위척도별로 가중 융합해 산출
    """
    if answers_by_source:
        # 하위척도별 소스별 값 수집
        by_sub: dict[str, dict] = {}
        for src, ans in answers_by_source.items():
            for it in PSY_ITEMS:
                if it["id"] in ans:
                    val = ans[it["id"]]
                    # 생태 하위척도는 역방향(dir=-1): 6-val 로 점수 보정(높을수록 양호)
                    score = (6 - val) if it["dir"] == -1 else val
                    by_sub.setdefault(it["sub"], {})[src] = score
        fused = _fuse_subscales(by_sub)
        # 기존 4이론 그룹핑으로 묶기
        grouped: dict[str, dict] = {}
        for sub, info in fused.items():
            theory = SUBSCALE_THEORY.get(sub, "self_determination")
            grouped.setdefault(theory, {})[sub] = info
        return grouped
    # 단일 dict 방식 (하위 호환): 기존 매핑 사용
    return {
        "self_determination": _subscale_scores(answers or {}, SDT_ITEMS),
        "self_regulated_learning": _subscale_scores(answers or {}, SRL_ITEMS),
        "positive_psychology": _subscale_scores(answers or {}, POSITIVE_PSYCH_ITEMS),
        "ecological_fit": _subscale_scores(answers or {}, ECOLOGICAL_ITEMS),
    }


_SDT_NARRATIVE = {
    "autonomy": "자율성(스스로 학습 목표·방법을 선택한다는 느낌)",
    "competence": "유능성(자신의 학습 능력에 대한 확신)",
    "relatedness": "관계성(교사·동료와의 정서적 연결)",
}
_SRL_NARRATIVE = {
    "planning": "학습 계획 수립 능력",
    "monitoring": "학습 과정 모니터링(메타인지) 능력",
    "evaluation": "학습 결과 자기평가 능력",
}
_PP_NARRATIVE = {
    "strengths_awareness": "자신의 강점 인식 정도",
    "wellbeing": "심리적 안녕감",
}
_ECO_NARRATIVE = {
    "classroom_fit": "교실 환경과의 적합도(낮을수록 불일치 큼)",
    "home_support": "가정 학습 지원 환경(낮을수록 불일치 큼)",
}


def to_consulting_context(scores: dict) -> str:
    """score_assessment() 결과를 ai_engine 프롬프트에 넣을 자연어 컨텍스트로 변환.

    PDF 3장에서 강조된 "생태학적 관점 / 데이터 기반 의사결정 / 협력적 관계" 원칙에 따라,
    점수를 학생 결함이 아닌 진단 데이터로 서술한다.
    """
    lines = []

    sdt = scores.get("self_determination", {})
    if sdt:
        lines.append("[자기결정성 이론(SDT) 기반 동기 진단]")
        for key, info in sdt.items():
            lines.append(f"- {_SDT_NARRATIVE.get(key, key)}: {info['score']}/5 ({info['level']})")

    srl = scores.get("self_regulated_learning", {})
    if srl:
        lines.append("[자기조절학습(SRL)/메타인지 진단]")
        for key, info in srl.items():
            lines.append(f"- {_SRL_NARRATIVE.get(key, key)}: {info['score']}/5 ({info['level']})")

    pp = scores.get("positive_psychology", {})
    if pp:
        lines.append("[긍정심리학 기반 진단]")
        for key, info in pp.items():
            lines.append(f"- {_PP_NARRATIVE.get(key, key)}: {info['score']}/5 ({info['level']})")

    eco = scores.get("ecological_fit", {})
    if eco:
        lines.append("[생태학적 관점: 학생-환경 적합도 (점수가 낮을수록 환경과의 불일치 큼)]")
        for key, info in eco.items():
            lines.append(f"- {_ECO_NARRATIVE.get(key, key)}: {info['score']}/5 ({info['level']})")

    if not lines:
        return "(심리 설문 응답 없음 — 학업 데이터만으로 컨설팅)"
    return "\n".join(lines)
