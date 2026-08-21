from __future__ import annotations

import argparse
import json
import platform
import random
import sys
from pathlib import Path

from consensus.ags_pbft_baseline import AGSConfig, AGSPBFTBaseline
from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from ml.features import NodeFeatures


def _features(rng: random.Random, malicious: bool) -> NodeFeatures:
    loss = min(1.0, max(0.0, rng.uniform(0.01, 0.25) + (0.35 if malicious else 0.0)))
    return NodeFeatures(agreement_rate=max(0.0, 1-loss), normalized_rtt=rng.uniform(0.05, 0.8), pdr=1-loss, link_quality=1-rng.uniform(0.02, 0.5), score_trend=rng.uniform(0.25, 0.9), recent_fault_rate=loss)


def run(variant: str, seed: int, density: int, output: Path, rounds: int = 100) -> Path:
    if density < 4: raise ValueError("density must be at least 4")
    rng, node_ids = random.Random(seed), [f"cav-{index:03d}" for index in range(density)]
    f = max(1, (density - 1) // 6)
    config = AGSConfig(min_consensus_nodes=3 * f + 1, reassignment_window=10)
    engine = MLAdaptiveAGSPBFT(node_ids, f, config) if variant == "ml" else AGSPBFTBaseline(node_ids, f, config)
    malicious = set(rng.sample(node_ids, min(f, len(node_ids) // 4)))
    rows = []
    for index in range(rounds):
        features = {node: _features(rng, node in malicious) for node in node_ids}
        agreed = {node for node in node_ids if node not in malicious or rng.random() < 0.12}
        latency_ms = 30 + density * 0.8 + sum(item.normalized_rtt for item in features.values()) / density * 50
        pdr = sum(item.pdr for item in features.values()) / density
        engine.record_round(agreed, str(index), {"density": density, "pdr": pdr, "latency_ms": latency_ms})
        if variant == "ml" and engine.request_count >= config.reassignment_window:
            engine.reassign_with_features(str(index), features, load=min(1.0, density / 300))
        if variant == "ml": engine.update_model(features, agreed)
        rows.append({"event":"metric","round_id":index,"density":density,"variant":variant,"latency_ms":latency_ms,"pdr":pdr,"throughput_packets":len(agreed),"consensus_size":len(engine.consensus_ids())})
    output.mkdir(parents=True, exist_ok=True)
    stem = output / f"{variant}_seed{seed}_density{density}"
    manifest = {"variant":variant,"seed":seed,"density":density,"rounds":rounds,"engine":"lightweight-equivalent-not-veins","python":sys.version,"platform":platform.platform(),"warning":"Development harness only; final paper evaluation requires documented SUMO/Veins/OMNeT++ integration."}
    stem.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with stem.with_suffix(".events.jsonl").open("w", encoding="utf-8") as handle:
        for row in [*engine.events, *rows]: handle.write(json.dumps(row, sort_keys=True) + "\n")
    return stem


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("baseline", "ml"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--density", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); print(run(args.variant, args.seed, args.density, args.output, args.rounds))


if __name__ == "__main__": main()
