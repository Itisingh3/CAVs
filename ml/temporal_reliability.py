"""Temporal, evidence-aware reliability scoring for AGS-PBFT.

The score deliberately separates a classifier's probability from three
interpretable evidence families.  The coefficients are fitted on held-out
calibration data; they are never chosen as paper-friendly constants.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ml.features import NodeFeatures


def _clip(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError("reliability evidence must be normalized to [0, 1]")
    return value


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


@dataclass(frozen=True)
class TemporalEvidence:
    """One causal node window; each field is available before selection.

    ``velocity_stability`` is used rather than raw speed so that every input
    has the same direction: larger values indicate more reliable evidence.
    """

    agreement_rate: float
    normalized_rtt: float
    pdr: float
    link_quality: float
    score_trend: float
    recent_fault_rate: float
    velocity_stability: float
    consensus_participation: float
    historical_reputation: float
    credential_trust: float

    def __post_init__(self) -> None:
        for value in self.as_vector():
            _clip(value)

    def as_vector(self) -> list[float]:
        return [
            self.agreement_rate, self.normalized_rtt, self.pdr,
            self.link_quality, self.score_trend, self.recent_fault_rate,
            self.velocity_stability, self.consensus_participation,
            self.historical_reputation, self.credential_trust,
        ]

    def base_features(self) -> NodeFeatures:
        """Projection used by the bounded online predictors."""
        return NodeFeatures(
            self.agreement_rate, self.normalized_rtt, self.pdr,
            self.link_quality, self.score_trend, self.recent_fault_rate,
        )

    def evidence_families(self, model_probability: float) -> tuple[float, float, float, float]:
        """Return (ML, historical, consensus, network), all in [0,1]."""
        _clip(model_probability)
        historical = (self.historical_reputation + self.score_trend + (1.0 - self.recent_fault_rate)) / 3.0
        consensus = (self.agreement_rate + self.consensus_participation + self.credential_trust) / 3.0
        network = ((1.0 - self.normalized_rtt) + self.pdr + self.link_quality + self.velocity_stability) / 4.0
        return model_probability, historical, consensus, network


@dataclass
class LearnedReliabilityScore:
    """A four-input logistic calibration layer fitted from labelled windows.

    The learned coefficients keep an auditable score while allowing the data
    to determine the relative influence of model, history, consensus, and
    network evidence.  Fit only after the base predictor has been frozen.
    """

    learning_rate: float = 0.08
    epochs: int = 300
    l2: float = 0.001
    intercept: float = 0.0
    coefficients: list[float] | None = None
    fitted: bool = False

    def __post_init__(self) -> None:
        if self.coefficients is None:
            self.coefficients = [0.0, 0.0, 0.0, 0.0]

    def predict(self, evidence: TemporalEvidence, model_probability: float) -> float:
        values = evidence.evidence_families(model_probability)
        return _sigmoid(self.intercept + sum(weight * value for weight, value in zip(self.coefficients or [], values)))

    def fit(self, rows: list[tuple[TemporalEvidence, float, bool]]) -> "LearnedReliabilityScore":
        if len(rows) < 8:
            raise ValueError("at least eight causal calibration windows are required")
        if len({label for _, _, label in rows}) != 2:
            raise ValueError("calibration windows must contain both reliability classes")
        for _ in range(self.epochs):
            grad_b = 0.0
            grad = [0.0, 0.0, 0.0, 0.0]
            for evidence, probability, label in rows:
                values = evidence.evidence_families(probability)
                error = self.predict(evidence, probability) - float(label)
                grad_b += error
                for index, value in enumerate(values):
                    grad[index] += error * value
            scale = 1.0 / len(rows)
            self.intercept -= self.learning_rate * grad_b * scale
            for index in range(4):
                self.coefficients[index] -= self.learning_rate * (grad[index] * scale + self.l2 * self.coefficients[index])
        self.fitted = True
        return self

    def normalized_influence(self) -> dict[str, float]:
        """Non-negative normalized coefficient magnitudes for reporting only."""
        names, magnitudes = ("ml_probability", "history", "consensus", "network"), [abs(value) for value in self.coefficients or []]
        total = sum(magnitudes)
        return {name: (value / total if total else 0.25) for name, value in zip(names, magnitudes)}
