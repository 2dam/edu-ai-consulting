"""FinBERT 기반 감정분석 — 뉴스 기사/댓글에서 학부모·학생 여론(긍정/중립/부정)을 감지("여론 평가" 기능).

교육 텍스트로 파인튜닝된 공개 모델이 마땅치 않아 금융 도메인 모델(FinBERT)을 그대로
가져다 쓴다. 금융 외 도메인에서도 zero-shot 성능은 괜찮지만, FinBERT 토크나이저가
영어 기준이라 한국어 텍스트에는 약하다 — FINBERT_MODEL_NAME 환경변수로 한국어 특화
모델(KoBERT 파인튜닝 등)로 손쉽게 교체할 수 있게 열어둔다.

transformers/torch는 선택적 의존성(requirements.txt 주석 참고, app/imputation.py의
VAE 경로와 동일한 패턴). 미설치거나 모델 다운로드가 실패하면 app.reputation_sentiment의
규칙 기반 스코어러로 자동 폴백해 "여론 평가"가 항상 응답하도록 한다 — 이 프로젝트의
"점수는 규칙 기반, AI는 보조" 원칙을 그대로 따른다.
"""
from __future__ import annotations

import os

from app.models_reputation import SentimentLabel
from app.reputation_sentiment import score_text as _rule_based_score

MODEL_NAME = os.environ.get("FINBERT_MODEL_NAME", "ProsusAI/finbert")

_pipeline = None
_pipeline_load_failed = False

_LABEL_MAP = {
    "positive": SentimentLabel.POSITIVE,
    "negative": SentimentLabel.NEGATIVE,
    "neutral": SentimentLabel.NEUTRAL,
}


def _get_pipeline():
    """FinBERT 파이프라인을 지연 로드 + 싱글턴 캐싱.

    실패하면 플래그를 남겨 이후 호출에서 재시도하지 않는다 — 매 요청마다 무거운
    임포트/모델 다운로드를 다시 시도하면 응답이 느려지고, 어차피 다시 실패할 확률이 높다.
    """
    global _pipeline, _pipeline_load_failed
    if _pipeline is not None or _pipeline_load_failed:
        return _pipeline

    try:
        import torch
        from transformers import pipeline

        _pipeline = pipeline(
            "sentiment-analysis",
            model=MODEL_NAME,
            device=0 if torch.cuda.is_available() else -1,
            top_k=None,
        )
    except Exception:
        _pipeline_load_failed = True
        return None
    return _pipeline


def analyze_sentiment(text: str) -> dict:
    """텍스트 하나를 감정분석.

    {"label": SentimentLabel, "score": float(0~1 신뢰도), "method": "finbert"|"rule_based"}
    를 반환한다. FinBERT 추론이 실패하거나 알 수 없는 라벨을 반환하면 규칙 기반으로 폴백.
    """
    text = (text or "").strip()
    if not text:
        return {"label": SentimentLabel.NEUTRAL, "score": 0.0, "method": "rule_based"}

    pipe = _get_pipeline()
    if pipe is not None:
        try:
            output = pipe(text[:512])
            # top_k=None이면 입력 1건당 전체 라벨 점수 리스트가 한 번 더 감싸져서 온다.
            scores = output[0] if output and isinstance(output[0], list) else output
            best = max(scores, key=lambda item: item["score"])
            label = _LABEL_MAP.get(str(best["label"]).lower())
            if label is not None:
                return {"label": label, "score": round(float(best["score"]), 3), "method": "finbert"}
        except Exception:
            pass  # 모델 추론 실패 시에도 아래 규칙 기반으로 폴백

    rule_score, rule_label = _rule_based_score(text)
    return {"label": rule_label, "score": round(abs(rule_score), 3), "method": "rule_based"}


def analyze_batch(texts: list[str]) -> list[dict]:
    return [analyze_sentiment(t) for t in texts]


def summarize_opinions(article_text: str, comment_bodies: list[str]) -> dict:
    """기사 본문 + 댓글들을 종합해 "여론 평가" 결과(긍정/중립/부정 비율)를 만든다."""
    comment_results = analyze_batch(comment_bodies)
    all_results = comment_results + ([analyze_sentiment(article_text)] if (article_text or "").strip() else [])

    counts = {label: 0 for label in SentimentLabel}
    for r in all_results:
        counts[r["label"]] += 1

    total = len(all_results)
    overall_label = max(counts, key=counts.get) if total else SentimentLabel.NEUTRAL
    method = "finbert" if any(r["method"] == "finbert" for r in all_results) else "rule_based"

    return {
        "overall_label": overall_label,
        "positive_count": counts[SentimentLabel.POSITIVE],
        "neutral_count": counts[SentimentLabel.NEUTRAL],
        "negative_count": counts[SentimentLabel.NEGATIVE],
        "total_analyzed": total,
        "method": method,
        "comment_sentiments": comment_results,
    }
