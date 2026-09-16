from __future__ import annotations

import math

from consensus.ags_pbft_baseline import AGSConfig, AGSPBFTBaseline
from ml.fallback_guard import should_fallback
from ml.features import NodeFeatures
from ml.predictor import OnlineLogisticReliability, ReliabilityPredictor
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence


class MLAdaptiveAGSPBFT(AGSPBFTBaseline):
    """Predictor-agnostic policy; uncertain decisions revert to the static control."""
    def __init__(self, node_ids: list[str], byzantine_tolerance: int, config: AGSConfig = AGSConfig(), predictor: ReliabilityPredictor | None = None, reliability_score: LearnedReliabilityScore | None = None):
        super().__init__(node_ids, byzantine_tolerance, config)
        self.predictor = predictor or OnlineLogisticReliability()
        self.reliability_score = reliability_score

    def record_round(self, agreed_node_ids: set[str], round_id: str, network_event: dict | None = None) -> None:
        """Preserve the paper's score update but defer membership to the ML policy.

        Calling the baseline method here would silently perform a static reassignment
        before the ML decision at every window, making the comparison invalid.
        """
        for node in self.nodes.values():
            delta = self.config.agreement_delta if node.node_id in agreed_node_ids else self.config.disagreement_delta
            node.score += delta; node.history.append(node.score)
            self.events.append({"event":"score_update","round_id":round_id,"node_id":node.node_id,"agreed":node.node_id in agreed_node_ids,"delta":delta,"score":node.score})
        self.request_count += 1
        if network_event: self.events.append({"event":"network","round_id":round_id, **network_event})

    def reassign_with_features(self, round_id: str, features: dict[str, NodeFeatures], load: float) -> None:
        try:
            probabilities = {node_id: self.predictor.predict(features[node_id]) for node_id in self.nodes}
            decision = should_fallback(list(probabilities.values()), self.predictor.observations)
        except (KeyError, ValueError):
            probabilities, decision = {}, should_fallback([], self.predictor.observations)
        if decision.use_static:
            self.events.append({"event":"ml_fallback","round_id":round_id,"reason":decision.reason})
            super().reassign(round_id); self.request_count = 0; return
        congestion = sum(1 - features[node_id].pdr + features[node_id].normalized_rtt for node_id in self.nodes) / (2 * len(self.nodes))
        target = max(3 * self.f + 1, self.config.min_consensus_nodes, math.ceil(len(self.nodes) * (0.35 + 0.3 * max(load, congestion))))
        ranked = sorted(self.nodes.values(), key=lambda node: (-probabilities[node.node_id], -node.score, node.node_id))
        selected = {node.node_id for node in ranked[:target]}
        for node in self.nodes.values():
            prior, node.group = node.group, "consensus" if node.node_id in selected else "candidate"
            if prior != node.group: self.events.append({"event":"group_transition","round_id":round_id,"node_id":node.node_id,"from":prior,"to":node.group,"score":node.score,"reliability":probabilities[node.node_id]})
        self.events.append({"event":"ml_reassignment","round_id":round_id,"target_size":target,"aggregate_congestion":congestion})
        self.request_count = 0

    def reassign_with_temporal_evidence(self, round_id: str, evidence: dict[str, TemporalEvidence], load: float) -> None:
        """Use a fitted score only when all causal evidence is available.

        This keeps the six-feature method as a backwards-compatible control;
        a partially populated temporal record cannot silently gain a score.
        """
        if self.reliability_score is None or not self.reliability_score.fitted:
            self.events.append({"event": "ml_fallback", "round_id": round_id, "reason": "unfitted_learned_score"})
            super().reassign(round_id); self.request_count = 0; return
        try:
            model_probabilities = {node_id: self.predictor.predict(item.base_features()) for node_id, item in evidence.items()}
        except (KeyError, ValueError):
            model_probabilities = {}
        self.reassign_with_temporal_probabilities(round_id, evidence, model_probabilities, load, observations=self.predictor.observations)

    def reassign_with_temporal_probabilities(self, round_id: str, evidence: dict[str, TemporalEvidence], model_probabilities: dict[str, float], load: float, *, observations: int, sequence_available: bool = True) -> None:
        """Deploy a pre-selected temporal model through the learned score.

        ``model_probabilities`` is ``P(reliable | X(t-K+1:t))`` from an
        adapter; it is not a consensus decision. Missing history/model output
        is explicit fallback, never a silent replacement with a hard label.
        """
        if self.reliability_score is None or not self.reliability_score.fitted:
            self.events.append({"event": "ml_fallback", "round_id": round_id, "reason": "unfitted_learned_score"})
            super().reassign(round_id); self.request_count = 0; return
        if not sequence_available:
            self.events.append({"event": "ml_fallback", "round_id": round_id, "reason": "sequence_unavailable"})
            super().reassign(round_id); self.request_count = 0; return
        try:
            base = {node_id: item.base_features() for node_id, item in evidence.items()}
            if set(evidence) != set(self.nodes) or set(model_probabilities) != set(self.nodes): raise ValueError("missing node evidence or probability")
            probabilities = {node_id: self.reliability_score.predict(item, model_probabilities[node_id]) for node_id, item in evidence.items()}
            decision = should_fallback(list(probabilities.values()), observations)
        except (KeyError, ValueError):
            probabilities, decision = {}, should_fallback([], observations)
        if decision.use_static:
            self.events.append({"event": "ml_fallback", "round_id": round_id, "reason": decision.reason})
            super().reassign(round_id); self.request_count = 0; return
        congestion = sum(1 - base[node_id].pdr + base[node_id].normalized_rtt for node_id in self.nodes) / (2 * len(self.nodes))
        target = max(3 * self.f + 1, self.config.min_consensus_nodes, math.ceil(len(self.nodes) * (0.35 + 0.3 * max(load, congestion))))
        ranked = sorted(self.nodes.values(), key=lambda node: (-probabilities[node.node_id], -node.score, node.node_id))
        selected = {node.node_id for node in ranked[:target]}
        for node in self.nodes.values():
            prior, node.group = node.group, "consensus" if node.node_id in selected else "candidate"
            if prior != node.group:
                self.events.append({"event": "group_transition", "round_id": round_id, "node_id": node.node_id, "from": prior, "to": node.group, "score": node.score, "reliability": probabilities[node.node_id]})
        self.events.append({"event": "ml_reassignment", "round_id": round_id, "target_size": target, "aggregate_congestion": congestion, "score_influence": self.reliability_score.normalized_influence()})
        self.request_count = 0

    def update_model(self, features: dict[str, NodeFeatures], agreed_node_ids: set[str]) -> None:
        for node_id, feature in features.items(): self.predictor.update(feature, node_id in agreed_node_ids)
