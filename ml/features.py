from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeFeatures:
    agreement_rate: float
    normalized_rtt: float
    pdr: float
    link_quality: float
    score_trend: float
    recent_fault_rate: float

    def as_vector(self) -> list[float]:
        values = [self.agreement_rate, self.normalized_rtt, self.pdr, self.link_quality, self.score_trend, self.recent_fault_rate]
        if any(not 0.0 <= value <= 1.0 for value in values): raise ValueError("all normalized features must be in [0, 1]")
        return values
