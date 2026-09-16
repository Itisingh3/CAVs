"""Execute reproducible model runs and aggregate locked-test mean ± standard deviation."""
from __future__ import annotations
import argparse
import csv
import subprocess
import sys
from pathlib import Path
from statistics import fmean, stdev

ALL_MODELS = ("logistic_regression", "decision_tree", "random_forest", "mlp", "lstm", "gru", "bilstm")
METRICS = ("accuracy", "precision", "recall", "f1", "auroc", "auprc", "true_positive", "true_negative", "false_positive", "false_negative")

def run(input_path: Path, output: Path, *, models: tuple[str, ...] = ALL_MODELS, seeds: tuple[int, ...] = (42, 43, 44, 45, 46), epochs: int | None = None, device: str | None = None) -> Path:
    output.mkdir(parents=True, exist_ok=True); gathered: dict[str, list[dict[str, str]]] = {model: [] for model in models}
    for model in models:
        for seed in seeds:
            report = output / f"{model}_seed{seed}.csv"
            command = [sys.executable, "-m", "ml.train", str(input_path), "--model", model, "--seed", str(seed), "--output", str(report), "--evaluate-locked-test"]
            if epochs is not None: command.extend(("--epochs", str(epochs)))
            if device is not None: command.extend(("--device", device))
            subprocess.run(command, check=True)
            with report.open(newline="", encoding="utf-8") as handle:
                locked = [row for row in csv.DictReader(handle) if row["stage"] == "locked_test"]
            if len(locked) != 1: raise RuntimeError(f"{report} has no single locked-test row")
            gathered[model].append(locked[0])
    summary = output / "model_multiseed_summary.csv"
    fields = ("model", "n_seeds", *[f"{metric}_mean" for metric in METRICS], *[f"{metric}_std" for metric in METRICS])
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for model, rows in gathered.items():
            result = {"model": model, "n_seeds": len(rows)}
            for metric in METRICS:
                values = [float(row[metric]) for row in rows]
                result[f"{metric}_mean"] = fmean(values); result[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
            writer.writerow(result)
    return summary

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("input", type=Path); parser.add_argument("--output", type=Path, default=Path("reports/ml_multiseed")); parser.add_argument("--models", nargs="+", choices=ALL_MODELS, default=list(ALL_MODELS)); parser.add_argument("--seeds", type=int, nargs="+", default=[42,43,44,45,46]); parser.add_argument("--epochs", type=int); parser.add_argument("--device"); args = parser.parse_args()
    print(run(args.input, args.output, models=tuple(args.models), seeds=tuple(args.seeds), epochs=args.epochs, device=args.device))
if __name__ == "__main__": main()
