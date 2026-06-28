"""
Comprehensive_Educational_Consulting_Psychology_Report.pdf 에서 정리된 핵심 이론을
정량 측정 가능한 형태로 코드화한 모듈.

- 자기결정성 이론 (Deci & Ryan, SDT): 자율성/유능성/관계성 3개 하위척도
- 자기조절학습 (SRL) / 메타인지: 계획-점검-평가 3개 하위척도
- 긍정심리학: 강점 인식 + 심리적 안녕감 2개 하위척도
- 생태학적 행동지원 (PBS/생태학적 관점): 학생-환경(교실/가정) 불일치 체크리스트

문항은 1~5점 리커트(answers: dict[item_id, int])로 입력받아 하위척도 평균을 내고,
ai_engine.generate_report 의 프롬프트 컨텍스트로 넘길 수 있는 해석 텍스트를 만든다.
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


def score_assessment(answers: dict[str, int]) -> dict:
    """심리 설문 응답을 채점해 이론별 하위척도 점수와 해석 라벨을 반환."""
    return {
        "self_determination": _subscale_scores(answers, SDT_ITEMS),
        "self_regulated_learning": _subscale_scores(answers, SRL_ITEMS),
        "positive_psychology": _subscale_scores(answers, POSITIVE_PSYCH_ITEMS),
        "ecological_fit": _subscale_scores(answers, ECOLOGICAL_ITEMS),
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
