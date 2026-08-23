from __future__ import annotations

import math

from consensus.ags_pbft_baseline import AGSConfig, AGSPBFTBaseline
from ml.fallback_guard import should_fallback
from ml.features import NodeFeatures
from ml.predictor import OnlineLogisticReliability


class MLAdaptiveAGSPBFT(AGSPBFTBaseline):
    """Online logistic policy; each decision transparently falls back to static when uncertain."""
    def __init__(self, node_ids: list[str], byzantine_tolerance: int, config: AGSConfig = AGSConfig(), predictor: OnlineLogisticReliability | None = None):
        super().__init__(node_ids, byzantine_tolerance, config)
        self.predictor = predictor or OnlineLogisticReliability()

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

    def update_model(self, features: dict[str, NodeFeatures], agreed_node_ids: set[str]) -> None:
        for node_id, feature in features.items(): self.predictor.update(feature, node_id in agreed_node_ids)
