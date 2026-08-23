"""Runs paired baseline/ML development-model experiments across a fixed seed set."""
from __future__ import annotations

import argparse
from pathlib import Path

from sim.run_experiment import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--density", type=int, required=True); parser.add_argument("--seed-start", type=int, default=1001)
    parser.add_argument("--seeds", type=int, default=30); parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--warmup-rounds", type=int, default=60); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 30: raise ValueError("paper-grade paired experiments require at least 30 seeds")
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for variant in ("baseline", "ml"):
            print(run(variant, seed, args.density, args.output, args.rounds, args.warmup_rounds))


if __name__ == "__main__": main()
