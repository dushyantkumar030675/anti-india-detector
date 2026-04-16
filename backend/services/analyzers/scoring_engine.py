"""
Threat Scoring Engine
Combines all signal scores into a single 0–100 threat score with severity label.
"""
from __future__ import annotations
from config.settings import get_settings

settings = get_settings()


def compute_threat_score(
    keyword_score: int,
    hate_confidence: float,
    hate_label: str,
    sentiment_score: float,
    bot_probability: float,
    coordination_score: float,
    reach_score: int,
    source_credibility: float = 0.5,
) -> dict:
    """
    Returns: {
        threat_score: int 0-100,
        severity: str,
        recommended_action: str,
        score_breakdown: dict
    }
    """
    # Classification signal (0–100)
    cls_score = 0
    if hate_label in ("hate", "offensive", "hateful"):
        cls_score = int(hate_confidence * 100)
    cls_score = max(cls_score, keyword_score)

    # Sentiment signal (0–100, only negative counts)
    sent_score = max(0, int(-sentiment_score * 100)) if sentiment_score < 0 else 0

    # Coordination signal (0–100)
    coord_score = int(
        max(bot_probability, coordination_score) * 100
    )

    # Source credibility (lower = more suspicious, 0–100 inverted)
    src_score = int((1 - source_credibility) * 100)

    # Weighted aggregate
    w = settings
    total = (
        cls_score   * w.weight_classification +
        sent_score  * w.weight_sentiment +
        coord_score * w.weight_coordination +
        src_score   * w.weight_source +
        reach_score * w.weight_reach
    )
    threat_score = min(100, max(0, int(total)))

    # Severity bands
    if threat_score >= settings.critical_threshold:
        severity = "critical"
        action = "escalate"
    elif threat_score >= settings.alert_threshold:
        severity = "high"
        action = "alert"
    elif threat_score >= 31:
        severity = "medium"
        action = "review"
    else:
        severity = "low"
        action = "log"

    return {
        "threat_score": threat_score,
        "severity": severity,
        "recommended_action": action,
        "score_breakdown": {
            "classification": cls_score,
            "sentiment": sent_score,
            "coordination": coord_score,
            "source": src_score,
            "reach": reach_score,
        },
    }
