"""Runtime composition of AKE-gated telemetry, temporal ML, and AGS-PBFT.

This module is the deployment boundary.  It deliberately accepts an
``AuthenticatedTelemetryContext`` rather than credentials, signatures, or
session keys.  Consequently, cryptographic verification remains upstream and
security-authoritative.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from ml.temporal_reliability import TemporalEvidence
from protocol.secure_session import AuthenticatedTelemetryContext, TelemetryHistory


class SequenceProbabilityModel(Protocol):
    """Compatible with ``TrainedSequenceModel`` without exposing torch here."""
    def predict_sequences(self, sequences: list[list[list[float]]]) -> list[float]: ...


@dataclass(frozen=True)
class NetworkTelemetry:
    normalized_rtt: float
    pdr: float
    link_quality: float
    velocity_stability: float


class AuthenticatedTelemetryStore:
    """Build causal ten-feature evidence scoped to verified AKE sessions."""
    def __init__(self) -> None:
        self._sessions: dict[str, AuthenticatedTelemetryContext] = {}
        self._history: dict[str, TelemetryHistory] = defaultdict(TelemetryHistory)

    def register(self, node_id: str, context: AuthenticatedTelemetryContext) -> None:
        if not node_id or not context.session_id or context.credential_trust != 1.0:
            raise ValueError("only a successful authenticated session may register telemetry")
        existing = self._sessions.get(node_id)
        if existing and existing.session_id != context.session_id:
            # A new AKE session resets temporal state; it must never blend sessions.
            self._history[node_id] = TelemetryHistory()
        self._sessions[node_id] = context

    def evidence(self, node_id: str, context: AuthenticatedTelemetryContext, network: NetworkTelemetry) -> TemporalEvidence:
        if self._sessions.get(node_id) != context:
            raise PermissionError("telemetry is not associated with this authenticated session")
        history = self._history[node_id]
        agreement = sum(history.agreements) / len(history.agreements) if history.agreements else .5
        faults = sum(history.faults[-10:]) / min(10, len(history.faults)) if history.faults else 0.0
        participation = sum(history.participations) / len(history.participations) if history.participations else .5
        score_trend = max(0.0, min(1.0, .5 + (history.reputation - .5) * .8))
        return TemporalEvidence(agreement, network.normalized_rtt, network.pdr, network.link_quality, score_trend, faults, network.velocity_stability, participation, history.reputation, context.credential_trust)

    def record_consensus_outcome(self, node_id: str, *, agreed: bool, participated: bool) -> None:
        if node_id not in self._sessions:
            raise PermissionError("cannot record unauthenticated telemetry")
        self._history[node_id].observe(agreed=agreed, participated=participated)


class SecureTemporalGroupingPipeline:
    """``AKE -> telemetry -> sequence P_ML -> score -> AGS-PBFT`` coordinator."""
    def __init__(self, engine: MLAdaptiveAGSPBFT, model: SequenceProbabilityModel, *, sequence_length: int = 20) -> None:
        if sequence_length < 1: raise ValueError("sequence_length must be positive")
        self.engine, self.model, self.sequence_length = engine, model, sequence_length
        self.telemetry = AuthenticatedTelemetryStore()
        self._windows: dict[str, deque[TemporalEvidence]] = {node: deque(maxlen=sequence_length) for node in engine.nodes}
        self._observation_counts: dict[str, int] = {node: 0 for node in engine.nodes}

    def register_session(self, node_id: str, context: AuthenticatedTelemetryContext) -> None:
        if node_id not in self.engine.nodes: raise KeyError(f"unknown consensus node {node_id}")
        self.telemetry.register(node_id, context); self._windows[node_id].clear(); self._observation_counts[node_id] = 0

    def group(self, round_id: str, contexts: dict[str, AuthenticatedTelemetryContext], network: dict[str, NetworkTelemetry], *, load: float) -> None:
        """Score the present causal window and request adaptive/static grouping.

        The current evidence is appended before inference, so each sequence is
        exactly ``X(t-K+1:t)``.  Outcomes are recorded separately afterwards.
        """
        try:
            evidence = {node: self.telemetry.evidence(node, contexts[node], network[node]) for node in self.engine.nodes}
        except (KeyError, PermissionError, ValueError):
            self.engine.reassign_with_temporal_probabilities(round_id, {}, {}, load, observations=0, sequence_available=False)
            return
        for node, item in evidence.items():
            self._windows[node].append(item); self._observation_counts[node] += 1
        if any(len(self._windows[node]) < self.sequence_length for node in self.engine.nodes):
            self.engine.reassign_with_temporal_probabilities(round_id, evidence, {}, load, observations=min(len(values) for values in self._windows.values()), sequence_available=False)
            return
        sequences = [[item.as_vector() for item in self._windows[node]] for node in self.engine.nodes]
        try:
            values = self.model.predict_sequences(sequences)
            probabilities = dict(zip(self.engine.nodes, values, strict=True))
            if any(not 0.0 <= value <= 1.0 for value in values): raise ValueError("invalid model probability")
        except (RuntimeError, ValueError, TypeError):
            self.engine.reassign_with_temporal_probabilities(round_id, evidence, {}, load, observations=0, sequence_available=False)
            return
        self.engine.reassign_with_temporal_probabilities(round_id, evidence, probabilities, load, observations=min(self._observation_counts.values()))

    def record_consensus_outcome(self, agreed_node_ids: set[str]) -> None:
        """Update history only after the consensus result is known."""
        for node in self.engine.nodes:
            self.telemetry.record_consensus_outcome(node, agreed=node in agreed_node_ids, participated=node in self.engine.consensus_ids())
