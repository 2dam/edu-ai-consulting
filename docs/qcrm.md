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

## Dashboard

The Next.js dashboard calls `/api/qcrm`, which proxies to the FastAPI backend.
If the backend is not running, the dashboard shows a deterministic sample result
so the UI can still be previewed.

The result is displayed in the right-side `Mini QCRM Diagnosis` panel. The
decision-adjustment layer appears inside the same panel as intervention fit and
confidence, so it does not become a second diagnosis widget.
