"""Execute a pre-registered, paired multi-seed development study.

This runner deliberately rejects fewer than 30 untouched test seeds.  It is a
reproducibility harness, not a substitute for SUMO/Veins/OMNeT++ measurements.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from sim.run_experiment import run
from sim.seed_manager import split_seeds, write_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--densities", type=int, nargs="+", default=[50, 100, 150, 200, 250, 300])
    parser.add_argument("--seed-start", type=int, default=1001)
    parser.add_argument("--total-seeds", type=int, default=150)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--warmup-rounds", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    seeds = list(range(arguments.seed_start, arguments.seed_start + arguments.total_seeds))
    split = split_seeds(seeds)
    if len(split.test) < 30: raise ValueError("configuration must reserve at least 30 untouched test seeds")
    arguments.output.mkdir(parents=True, exist_ok=True)
    write_manifest(arguments.output / "seed_manifest.csv", split)
    study_manifest = {
        "study_type": "controlled-development-model-not-veins",
        "densities": arguments.densities,
        "rounds": arguments.rounds,
        "warmup_rounds": arguments.warmup_rounds,
        "seed_split": {name: list(getattr(split, name)) for name in ("train", "validation", "test")},
        "evaluation_split": "test",
        "pairing": "baseline and ml share every base seed and derived stream seed",
        "platform": platform.platform(),
        "warning": "Not a SUMO/Veins/OMNeT++ result; do not use as networking-letter performance evidence.",
    }
    (arguments.output / "study_manifest.json").write_text(json.dumps(study_manifest, indent=2), encoding="utf-8")
    for density in arguments.densities:
        for seed in split.test:
            for variant in ("baseline", "ml"):
                print(run(variant, seed, density, arguments.output, arguments.rounds, arguments.warmup_rounds))


if __name__ == "__main__": main()
