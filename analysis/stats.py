from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev


def mean_ci95(values: list[float]) -> tuple[float, float]:
    if not values: raise ValueError("no values")
    if len(values) == 1: return values[0], 0.0
    return fmean(values), 1.96 * stdev(values) / math.sqrt(len(values))


METRICS = ("latency_ms", "pdr", "throughput_packets", "consensus_size", "control_bytes", "committed", "false_removals", "malicious_selected")


def _run_means(path: Path) -> tuple[tuple[str, int, int], dict[str, float]] | None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    evaluation = [row for row in rows if row.get("event") == "metric" and row.get("phase") == "evaluation"]
    if not evaluation: return None
    key = (evaluation[0]["variant"], int(evaluation[0]["density"]), int(evaluation[0]["seed"]))
    return key, {metric: fmean(float(row[metric]) for row in evaluation) for metric in METRICS}


def _cohen_dz(differences: list[float]) -> float:
    return 0.0 if len(differences) < 2 or stdev(differences) == 0 else fmean(differences) / stdev(differences)


def aggregate(input_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    # A run/seed, not an individual round, is the independent observation.
    runs: dict[tuple[str, int, int], dict[str, float]] = {}
    for path in input_dir.glob("*.events.jsonl"):
        result = _run_means(path)
        if result: runs[result[0]] = result[1]
    grouped: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (variant, density, _), metrics in runs.items():
        for metric, value in metrics.items(): grouped[(variant, density)][metric].append(value)
    output_dir.mkdir(parents=True, exist_ok=True); target, paired_target = output_dir / "summary.csv", output_dir / "paired_comparison.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant","density","metric","n_seeds","mean","ci95"]); writer.writeheader()
        for (variant, density), metrics in sorted(grouped.items()):
            for metric, values in sorted(metrics.items()):
                mean, ci = mean_ci95(values); writer.writerow({"variant":variant,"density":density,"metric":metric,"n_seeds":len(values),"mean":mean,"ci95":ci})
    with paired_target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["density","metric","n_pairs","baseline_mean","ml_mean","ml_minus_baseline","difference_ci95","cohen_dz","paired_t_statistic"]); writer.writeheader()
        densities = sorted({density for _, density, _ in runs})
        for density in densities:
            baseline_seeds = {seed for variant, d, seed in runs if variant == "baseline" and d == density}
            ml_seeds = {seed for variant, d, seed in runs if variant == "ml" and d == density}
            for metric in METRICS:
                seeds = sorted(baseline_seeds & ml_seeds)
                baseline, ml = [runs[("baseline", density, seed)][metric] for seed in seeds], [runs[("ml", density, seed)][metric] for seed in seeds]
                if not baseline: continue
                differences = [m - b for b, m in zip(baseline, ml)]; delta, ci = mean_ci95(differences)
                t = 0.0 if len(differences) < 2 or stdev(differences) == 0 else delta / (stdev(differences) / math.sqrt(len(differences)))
                writer.writerow({"density":density,"metric":metric,"n_pairs":len(seeds),"baseline_mean":fmean(baseline),"ml_mean":fmean(ml),"ml_minus_baseline":delta,"difference_ci95":ci,"cohen_dz":_cohen_dz(differences),"paired_t_statistic":t})
    return target, paired_target


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("input", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); print(*aggregate(args.input, args.output), sep="\n")


if __name__ == "__main__": main()
