"""Generate paper-ready plots only from paired run-level output files."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def _load(path: Path) -> dict[str, dict[int, dict[str, float]]]:
    data: dict[str, dict[int, dict[str, float]]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            density, metric = int(row["density"]), row["metric"]
            data[metric][density] = {key: float(value) for key, value in row.items() if key not in {"density", "metric"}}
    return data


def _load_summary(path: Path) -> dict[str, dict[int, dict[str, dict[str, float]]]]:
    data: dict[str, dict[int, dict[str, dict[str, float]]]] = defaultdict(lambda: defaultdict(dict))
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            data[row["metric"]][int(row["density"])][row["variant"]] = {"mean": float(row["mean"]), "ci95": float(row["ci95"])}
    return data


def paired_development_figure(paired_csv: Path, summary_csv: Path, output: Path) -> tuple[Path, Path]:
    if not paired_csv.is_file(): raise FileNotFoundError("expected paired_comparison.csv")
    import matplotlib.pyplot as plt
    data, summary = _load(paired_csv), _load_summary(summary_csv); densities = sorted(data["latency_ms"])
    blue, orange, green, red, grey = "#1F5A99", "#D97904", "#198754", "#B42318", "#526D82"
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":9, "axes.labelsize":9, "axes.titlesize":10, "legend.fontsize":8})
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.45), constrained_layout=True)
    def series(metric: str, field: str): return [data[metric][density][field] for density in densities]
    def ci(metric: str, variant: str): return [summary[metric][density][variant]["ci95"] for density in densities]
    # (a) latency
    axes[0].errorbar(densities, series("latency_ms", "baseline_mean"), yerr=ci("latency_ms", "baseline"), marker="o", color=blue, linewidth=1.8, capsize=3, label="Best static")
    axes[0].errorbar(densities, series("latency_ms", "ml_mean"), yerr=ci("latency_ms", "ml"), marker="s", color=orange, linewidth=1.8, capsize=3, label="ML-adaptive")
    axes[0].set_title("(a) End-to-end latency"); axes[0].set_xlabel("Vehicle density"); axes[0].set_ylabel("Latency (ms)"); axes[0].legend(frameon=False); axes[0].grid(axis="y", alpha=.22)
    # (b) dual metrics, separate y axes
    axb = axes[1]; axb2 = axb.twinx()
    first = axb.errorbar(densities, series("throughput_packets", "baseline_mean"), yerr=ci("throughput_packets", "baseline"), marker="o", color=blue, linewidth=1.8, capsize=3, label="Static throughput")
    second = axb.errorbar(densities, series("throughput_packets", "ml_mean"), yerr=ci("throughput_packets", "ml"), marker="s", color=orange, linewidth=1.8, capsize=3, label="ML throughput")
    third = axb2.errorbar(densities, series("pdr", "baseline_mean"), yerr=ci("pdr", "baseline"), marker="o", linestyle="--", color=green, linewidth=1.6, capsize=3, label="Static PDR")
    fourth = axb2.errorbar(densities, series("pdr", "ml_mean"), yerr=ci("pdr", "ml"), marker="s", linestyle="--", color=red, linewidth=1.6, capsize=3, label="ML PDR")
    axb.set_title("(b) Throughput and delivery"); axb.set_xlabel("Vehicle density"); axb.set_ylabel("Throughput (packets/round)"); axb2.set_ylabel("Packet delivery ratio"); axb.grid(axis="y", alpha=.22)
    axb.legend([first, second, third, fourth], ["Static throughput", "ML throughput", "Static PDR", "ML PDR"], frameon=False, loc="upper left")
    # (c) trust-response timing and collateral harm, with separate physical units.
    axc = axes[2]; axc2 = axc.twinx()
    first = axc.errorbar(densities, series("malicious_removal_time", "baseline_mean"), yerr=ci("malicious_removal_time", "baseline"), marker="o", color=blue, linewidth=1.8, capsize=3, label="Static removal time")
    second = axc.errorbar(densities, series("malicious_removal_time", "ml_mean"), yerr=ci("malicious_removal_time", "ml"), marker="s", color=orange, linewidth=1.8, capsize=3, label="ML removal time")
    third = axc2.errorbar(densities, [100 * value for value in series("false_removal_rate", "baseline_mean")], yerr=[100 * value for value in ci("false_removal_rate", "baseline")], marker="o", linestyle="--", color=green, linewidth=1.6, capsize=3, label="Static false removal")
    fourth = axc2.errorbar(densities, [100 * value for value in series("false_removal_rate", "ml_mean")], yerr=[100 * value for value in ci("false_removal_rate", "ml")], marker="s", linestyle="--", color=red, linewidth=1.6, capsize=3, label="ML false removal")
    axc.set_title("(c) Trust-response performance"); axc.set_xlabel("Vehicle density"); axc.set_ylabel("Malicious-node removal time (rounds)"); axc2.set_ylabel("Honest-node false-removal rate (%)"); axc.legend([first, second, third, fourth], ["Static removal time", "ML removal time", "Static false removal", "ML false removal"], frameon=False, fontsize=7.1, loc="upper left"); axc.grid(axis="y", alpha=.22)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False); axis.set_xticks(densities)
    fig.text(.5, -.035, "Controlled development model, 30 paired seeds per density; error bars are 95% CIs across seeds. Not a SUMO/Veins or real-network claim.", ha="center", color=grey, fontsize=8)
    output.parent.mkdir(parents=True, exist_ok=True)
    svg, png = output.with_suffix(".svg"), output.with_suffix(".png")
    fig.savefig(svg, bbox_inches="tight"); fig.savefig(png, dpi=240, bbox_inches="tight"); plt.close(fig)
    return svg, png


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("paired_csv", type=Path); parser.add_argument("--summary", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); print(*paired_development_figure(args.paired_csv, args.summary, args.output), sep="\n")


if __name__ == "__main__": main()
