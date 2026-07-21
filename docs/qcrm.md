# QCRM 기본진단 (Basic Diagnosis)

QCRM 기본진단은 교육 컨설팅을 위한 소형 학습 사고 진단 모델입니다.
It is designed as a consulting aid, not as a standardized psychological test or
quantum-hardware execution.


## Basic behavior items

기본진단의 행동 기반 미니 문제는 특정 과목의 성취도에 편중되지 않도록
국어·영어·수학·사회·과학·통합 영역에서 한 문항씩 구성합니다. 각 문항은
교과 지식 자체보다 핵심 조건 파악, 전략 선택, 계산 정확도, 주의 조절,
시간 관리와 같은 QCRM 요인을 관찰하는 데 목적이 있습니다.

문항 데이터는 [qcrm-basic-items.json](qcrm-basic-items.json)에 저장합니다.
향후 150문항 심화진단은 기본진단과 별도 버전 및 문항은행으로 관리합니다.

## Backend

Endpoint:

```http
POST /qcrm-assessment
```

Example request:

```json
{
  "profile": {
    "concept_mastery": 0.62,
    "problem_interpretation": 0.48,
    "strategy_selection": 0.42,
    "calculation_accuracy": 0.74,
    "attention_control": 0.52,
    "time_management": 0.45
  },
  "iterations": 3
}
```

The engine returns learning-state probabilities, weakest links, strongest links,
recommendations, a decision-adjustment layer for intervention fit, and a short
consulting narrative.

## Landing page

The interactive diagnosis lives in the landing page's Chapter 6
("Mini QCRM Diagnosis"), served from `api/app/static/landing.html`. It calls
`/qcrm-assessment` directly (same origin as the landing page, no dashboard
proxy) and renders the readiness score, weakest/strongest links,
recommendations, and decision-adjustment layer inline in that chapter.

The old floating `QcrmPanel` on the EduIntel map dashboard
(`dashboard/src/app/page.tsx`) was removed since it duplicated this chapter.
