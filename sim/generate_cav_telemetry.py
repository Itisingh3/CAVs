"""Export causal CAV telemetry windows from the controlled AGS-PBFT model.

This is labelled *simulated CAV telemetry*, not ROAD data or a real-network
claim.  Features at round ``t`` use only network measurements and node history
available before that round's consensus outcome; ``reliable`` is the ensuing
round outcome and is never a feature.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path

from data.preprocess_road import scenario_split
from ml.train_temporal_pipeline import FEATURE_COLUMNS
from sim.run_experiment import NodeCondition, _features, _round_outcome, _update_conditions

COLUMNS = ("split", "scenario_id", "node_id", "window_index", "reliable", *FEATURE_COLUMNS)

def _clip(value: float) -> float: return max(0.0, min(1.0, value))

def generate_scenario(seed: int, rounds: int, density: int) -> list[dict[str, object]]:
    """Generate one complete split-safe scenario; no ROAD fields are involved."""
    rng, scenario = random.Random(seed), f"simulated-cav-{seed}"
    network_rng, outcome_rng = random.Random(seed + 101), random.Random(seed + 202)
    node_ids = [f"cav-{index:03d}" for index in range(density)]
    malicious = set(rng.sample(node_ids, max(1, density // 6)))
    conditions = {node: NodeCondition(rng.uniform(.62, .98), node in malicious) for node in node_ids}
    history = {node: {"agreed": [], "selected": [], "fault": [], "reputation": .5} for node in node_ids}
    rows = []
    for index in range(rounds):
        congestion = _clip(.20 + .18 * (1 + math.sin(index / 17)) / 2 + network_rng.uniform(-.06, .06))
        observed = {node: _features(network_rng, conditions[node], congestion) for node in node_ids}
        # Feature extraction happens before the consensus outcome below.
        feature_rows = {}
        for node, item in observed.items():
            prior = history[node]; agreements, faults, selected = prior["agreed"], prior["fault"], prior["selected"]
            agreement_rate = sum(agreements) / len(agreements) if agreements else .5
            recent_fault = sum(faults[-10:]) / min(10, len(faults)) if faults else .0
            participation = sum(selected) / len(selected) if selected else .5
            score_trend = _clip(.5 + (prior["reputation"] - .5) * .8)
            feature_rows[node] = [agreement_rate, item.normalized_rtt, item.pdr, item.link_quality, score_trend, recent_fault, _clip(.75 - congestion * .3 + network_rng.uniform(-.1, .1)), participation, _clip(prior["reputation"]), 1.0]
        selected_ids = set(node_ids)  # Telemetry collection occurs before a learned group is deployed.
        outcome = _round_outcome(outcome_rng, selected_ids, conditions, observed, max(1, (density - 1) // 6), density, congestion)
        for node in node_ids:
            reliable = node in outcome["agreed"]
            prior = history[node]; prior["agreed"].append(float(reliable)); prior["fault"].append(float(not reliable)); prior["selected"].append(1.0)
            prior["reputation"] = _clip(.9 * prior["reputation"] + .1 * float(reliable))
            rows.append({"split": scenario_split(scenario), "scenario_id": scenario, "node_id": node, "window_index": index, "reliable": int(reliable), **dict(zip(FEATURE_COLUMNS, feature_rows[node]))})
        _update_conditions(rng, conditions, congestion)
    return rows

def generate(output: Path, *, scenarios: int = 24, rounds: int = 100, density: int = 12, seed: int = 42) -> int:
    if scenarios < 3 or rounds < 2 or density < 4: raise ValueError("scenarios >= 3, rounds >= 2, and density >= 4 are required")
    rows = [row for offset in range(scenarios) for row in generate_scenario(seed + offset, rounds, density)]
    if len({row["split"] for row in rows}) != 3: raise ValueError("choose more scenarios or another seed so all train/validation/test splits exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS); writer.writeheader(); writer.writerows(rows)
    return len(rows)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate causal simulated CAV reliability telemetry; never derives it from ROAD.")
    parser.add_argument("--output", type=Path, default=Path("data/derived/cav_reliability_windows.csv")); parser.add_argument("--scenarios", type=int, default=24); parser.add_argument("--rounds", type=int, default=100); parser.add_argument("--density", type=int, default=12); parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(); print(f"wrote_windows={generate(args.output, scenarios=args.scenarios, rounds=args.rounds, density=args.density, seed=args.seed)}\noutput={args.output}")
if __name__ == "__main__": main()
