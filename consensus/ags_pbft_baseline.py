from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import fmean, pstdev


@dataclass(frozen=True)
class AGSConfig:
    initial_score: float = 100.0
    agreement_delta: float = 1.0
    disagreement_delta: float = -5.0
    threshold_multiplier: float = 1.0
    reassignment_window: int = 50
    consensus_fraction: float = 0.5
    min_consensus_nodes: int = 4


@dataclass
class NodeState:
    node_id: str
    score: float = 100.0
    group: str = "candidate"
    history: list[float] = field(default_factory=list)


class AGSPBFTBaseline:
    """Faithful base-paper defaults: 100 score, +1/-5, mu+-sigma, every 50 requests."""
    def __init__(self, node_ids: list[str], byzantine_tolerance: int, config: AGSConfig = AGSConfig()):
        if len(node_ids) < 3 * byzantine_tolerance + 1: raise ValueError("PBFT requires n >= 3f+1")
        self.config, self.f, self.request_count = config, byzantine_tolerance, 0
        self.nodes = {node_id: NodeState(node_id, config.initial_score, history=[config.initial_score]) for node_id in node_ids}
        self.events: list[dict] = []
        self._assign_initial_consensus()

    def _target_size(self) -> int:
        return max(3 * self.f + 1, self.config.min_consensus_nodes, math.ceil(len(self.nodes) * self.config.consensus_fraction))

    def _assign_initial_consensus(self) -> None:
        for node in sorted(self.nodes.values(), key=lambda n: n.node_id)[:self._target_size()]: node.group = "consensus"

    def record_round(self, agreed_node_ids: set[str], round_id: str, network_event: dict | None = None) -> None:
        for node in self.nodes.values():
            delta = self.config.agreement_delta if node.node_id in agreed_node_ids else self.config.disagreement_delta
            node.score += delta; node.history.append(node.score)
            self.events.append({"event":"score_update","round_id":round_id,"node_id":node.node_id,"agreed":node.node_id in agreed_node_ids,"delta":delta,"score":node.score})
        self.request_count += 1
        if network_event: self.events.append({"event":"network","round_id":round_id, **network_event})
        if self.request_count >= self.config.reassignment_window:
            self.reassign(round_id); self.request_count = 0

    def reassign(self, round_id: str) -> None:
        scores = [node.score for node in self.nodes.values()]
        mu, sigma = fmean(scores), pstdev(scores) if len(scores) > 1 else 0.0
        lower, upper = mu - self.config.threshold_multiplier * sigma, mu + self.config.threshold_multiplier * sigma
        ranked = sorted(self.nodes.values(), key=lambda n: (-n.score, n.node_id))
        target = self._target_size()
        selected = {node.node_id for node in ranked[:target]}
        for node in self.nodes.values():
            prior, node.group = node.group, "consensus" if node.node_id in selected else "candidate"
            if prior != node.group: self.events.append({"event":"group_transition","round_id":round_id,"node_id":node.node_id,"from":prior,"to":node.group,"score":node.score,"lower_threshold":lower,"upper_threshold":upper})
        self.events.append({"event":"reassignment","round_id":round_id,"mu":mu,"sigma":sigma,"lower_threshold":lower,"upper_threshold":upper,"target_size":target})

    def consensus_ids(self) -> set[str]: return {node.node_id for node in self.nodes.values() if node.group == "consensus"}
