from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FallbackDecision:
    use_static: bool
    reason: str | None


def should_fallback(probabilities: list[float], observations: int, confidence_threshold: float = 0.20, min_observations: int = 10) -> FallbackDecision:
    if observations < min_observations: return FallbackDecision(True, "insufficient_labeled_observations")
    if not probabilities or any(not 0.0 <= probability <= 1.0 for probability in probabilities): return FallbackDecision(True, "invalid_prediction")
    confidence = sum(abs(probability - 0.5) * 2 for probability in probabilities) / len(probabilities)
    return FallbackDecision(confidence < confidence_threshold, "low_model_confidence" if confidence < confidence_threshold else None)
