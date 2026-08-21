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


def aggregate(input_dir: Path, output_dir: Path) -> Path:
    grouped: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for path in input_dir.glob("*.events.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("event") == "metric":
                bucket = grouped[(row["variant"], row["density"])]
                for metric in ("latency_ms", "pdr", "throughput_packets", "consensus_size"): bucket[metric].append(float(row[metric]))
    output_dir.mkdir(parents=True, exist_ok=True); target = output_dir / "summary.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant","density","metric","n","mean","ci95"]); writer.writeheader()
        for (variant, density), metrics in sorted(grouped.items()):
            for metric, values in sorted(metrics.items()):
                mean, ci = mean_ci95(values); writer.writerow({"variant":variant,"density":density,"metric":metric,"n":len(values),"mean":mean,"ci95":ci})
    return target


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("input", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); print(aggregate(args.input, args.output))


if __name__ == "__main__": main()
