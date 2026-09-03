from __future__ import annotations

import argparse
import json
import platform
import random
import math
import sys
from pathlib import Path
from dataclasses import dataclass
from statistics import fmean

from consensus.ags_pbft_baseline import AGSConfig, AGSPBFTBaseline
from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from ml.features import NodeFeatures
from sim.seed_manager import derive_streams


@dataclass
class NodeCondition:
    reliability: float
    malicious: bool


def _features(rng: random.Random, condition: NodeCondition, congestion: float) -> NodeFeatures:
    """Observable features correlate with, but do not disclose, future reliability."""
    jitter = lambda amount: rng.uniform(-amount, amount)
    reliability = max(0.0, min(1.0, condition.reliability + jitter(0.08)))
    loss = max(0.0, min(1.0, 1.0 - reliability + congestion * 0.20 + jitter(0.05)))
    return NodeFeatures(max(0.0, min(1.0, reliability + jitter(0.08))), max(0.0, min(1.0, .12 + congestion * .65 + (1 - reliability) * .25 + jitter(.06))), 1 - loss, max(0.0, min(1.0, reliability - congestion * .12 + jitter(.08))), max(0.0, min(1.0, reliability + jitter(.12))), max(0.0, min(1.0, loss + (.45 if condition.malicious else 0))))


def _update_conditions(rng: random.Random, conditions: dict[str, NodeCondition], congestion: float) -> None:
    for condition in conditions.values():
        drift = rng.uniform(-.09, .09) - congestion * .06 - (rng.uniform(.08, .30) if condition.malicious else 0)
        condition.reliability = max(.02, min(.98, condition.reliability + .17 * drift))


def _round_outcome(rng: random.Random, selected_ids: set[str], conditions: dict[str, NodeCondition], features: dict[str, NodeFeatures], f: int, density: int, congestion: float) -> dict:
    selected = [conditions[node] for node in selected_ids]
    agreed = {node for node in selected_ids if rng.random() < conditions[node].reliability and not (conditions[node].malicious and rng.random() < .78)}
    committed = len(agreed) >= 2 * f + 1
    reliability = sum(conditions[node].reliability for node in selected_ids) / len(selected_ids)
    malicious_fraction = sum(node.malicious for node in selected) / len(selected)
    mean_rtt = sum(features[node].normalized_rtt for node in selected_ids) / len(selected_ids)
    false_removals = sum(1 for node, state in conditions.items() if not state.malicious and node not in selected_ids)
    honest_nodes = sum(1 for state in conditions.values() if not state.malicious)
    return {"agreed": agreed, "latency_ms": 20 + density * .35 + mean_rtt * 45 + len(selected_ids) * 1.8 + malicious_fraction * 90 + (0 if committed else 120), "throughput_packets": max(0.0, (len(agreed) if committed else 0) * (1 - congestion * .30)), "pdr": max(0.0, min(1.0, reliability * (1 - congestion * .22) * (1 - malicious_fraction * .35))), "control_bytes": len(selected_ids) * 3309 * 3, "committed": float(committed), "false_removals": float(false_removals), "false_removal_rate": false_removals / honest_nodes, "malicious_selected": float(sum(1 for node in selected_ids if conditions[node].malicious))}


def run(variant: str, seed: int, density: int, output: Path, rounds: int = 300, warmup_rounds: int = 60) -> Path:
    if density < 4: raise ValueError("density must be at least 4")
    if rounds <= warmup_rounds: raise ValueError("rounds must exceed warmup_rounds")
    streams = derive_streams(seed)
    initialization_rng = random.Random(seed)
    mobility_rng = random.Random(streams["mobility"])
    channel_rng = random.Random(streams["channel"])
    traffic_rng = random.Random(streams["traffic"])
    attack_rng = random.Random(streams["attack"])
    node_ids = [f"cav-{index:03d}" for index in range(density)]
    f = max(1, (density - 1) // 6)
    config = AGSConfig(min_consensus_nodes=3 * f + 1, reassignment_window=10)
    engine = MLAdaptiveAGSPBFT(node_ids, f, config) if variant == "ml" else AGSPBFTBaseline(node_ids, f, config)
    malicious = set(attack_rng.sample(node_ids, min(f, len(node_ids) // 4)))
    conditions = {node: NodeCondition(initialization_rng.uniform(.62, .98), node in malicious) for node in node_ids}
    rows = []
    removal_started: dict[str, int] = {}
    removal_delays: list[float] = []
    for index in range(rounds):
        congestion = min(.95, max(.05, density / 350 + .23 * (1 + math.sin(index / 17)) / 2 + channel_rng.uniform(-.08, .08)))
        features = {node: _features(channel_rng, conditions[node], congestion) for node in node_ids}
        outcome = _round_outcome(traffic_rng, engine.consensus_ids(), conditions, features, f, density, congestion)
        engine.record_round(outcome["agreed"], str(index), {"density": density, "pdr": outcome["pdr"], "latency_ms": outcome["latency_ms"], "congestion": congestion})
        if variant == "ml":
            engine.update_model(features, outcome["agreed"])
            if engine.request_count >= config.reassignment_window: engine.reassign_with_features(str(index), features, load=congestion)
        current_consensus = engine.consensus_ids()
        for node in malicious:
            if node in current_consensus and node not in removal_started:
                removal_started[node] = index
            elif node not in current_consensus and node in removal_started:
                removal_delays.append(float(index - removal_started.pop(node) + 1))
        _update_conditions(mobility_rng, conditions, congestion)
        rows.append({"event":"metric","round_id":index,"phase":"evaluation" if index >= warmup_rounds else "warmup","density":density,"variant":variant,"seed":seed, **{key:value for key, value in outcome.items() if key != "agreed"},"consensus_size":len(engine.consensus_ids())})
    # A malicious node never removed during a run is right-censored at the run length.
    removal_time = fmean(removal_delays) if removal_delays else float(rounds)
    for row in rows:
        if row["phase"] == "evaluation": row["malicious_removal_time"] = removal_time
    output.mkdir(parents=True, exist_ok=True)
    stem = output / f"{variant}_seed{seed}_density{density}"
    manifest = {"variant":variant,"seed":seed,"seed_streams":streams,"density":density,"rounds":rounds,"warmup_rounds":warmup_rounds,"engine":"controlled-development-model-not-veins","paired_seed":seed,"python":sys.version,"platform":platform.platform(),"warning":"Development model only. Do not cite these as SUMO/Veins/OMNeT++ or real-network results."}
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with stem.with_suffix(".events.jsonl").open("w", encoding="utf-8") as handle:
        for row in [*engine.events, *rows]: handle.write(json.dumps(row, sort_keys=True) + "\n")
    return stem


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("baseline", "ml"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--density", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--warmup-rounds", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); print(run(args.variant, args.seed, args.density, args.output, args.rounds, args.warmup_rounds))


if __name__ == "__main__": main()
