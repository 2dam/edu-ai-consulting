# Mini QCRM Learning Diagnosis

Mini QCRM is a small quantum-inspired diagnosis model for education consulting.
It is designed as a consulting aid, not as a standardized psychological test or
quantum-hardware execution.

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
