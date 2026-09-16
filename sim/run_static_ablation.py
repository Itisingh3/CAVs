"""Validation-only static AGS-PBFT sweep and immutable configuration lock."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import fmean

from analysis.ablation_sweep import static_configurations
from consensus.ags_pbft_baseline import AGSConfig
from sim.run_experiment import run

def _score(stems: list[Path]) -> tuple[float, float, float]:
    rows = []
    for stem in stems:
        rows.extend(json.loads(line) for line in stem.with_suffix(".events.jsonl").read_text(encoding="utf-8").splitlines())
    evaluation = [row for row in rows if row.get("event") == "metric" and row.get("phase") == "evaluation"]
    # Pre-registered lexicographic objective: commit success, PDR, then lower latency.
    return fmean(row["committed"] for row in evaluation), fmean(row["pdr"] for row in evaluation), -fmean(row["latency_ms"] for row in evaluation)

def sweep(output: Path, *, density: int, seeds: list[int], rounds: int, warmup_rounds: int) -> dict:
    output.mkdir(parents=True, exist_ok=True); candidates = []
    for index, values in enumerate(static_configurations()):
        config = AGSConfig(min_consensus_nodes=3 * max(1, (density - 1) // 6), **values)
        stems = [run("baseline", seed, density, output / f"candidate_{index:02d}", rounds, warmup_rounds, ags_config=config) for seed in seeds]
        candidates.append({"candidate": index, "config": values, "validation_score": list(_score(stems))})
    winner = max(candidates, key=lambda row: tuple(row["validation_score"]))
    locked = {"selection_split": "development_validation_only", "selection_seeds": seeds, "density": density, "rounds": rounds, "warmup_rounds": warmup_rounds, "objective": ["mean_consensus_success", "mean_pdr", "negative_mean_latency_ms"], "winner": winner, "warning": "This lock is for the controlled development model. Re-lock on real trace validation data before paper claims."}
    (output / "static_config_lock.json").write_text(json.dumps(locked, indent=2), encoding="utf-8")
    return locked

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--density", type=int, default=30); parser.add_argument("--seed-start", type=int, default=101); parser.add_argument("--seeds", type=int, default=10); parser.add_argument("--rounds", type=int, default=150); parser.add_argument("--warmup-rounds", type=int, default=50); args = parser.parse_args()
    print(json.dumps(sweep(args.output, density=args.density, seeds=list(range(args.seed_start, args.seed_start + args.seeds)), rounds=args.rounds, warmup_rounds=args.warmup_rounds), indent=2))
if __name__ == "__main__": main()
