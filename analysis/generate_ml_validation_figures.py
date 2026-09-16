"""Generate ML validation figures from the repository's deterministic development model.

The generated figures are explicitly development-harness artifacts.  They are
useful to validate the predictor-comparison pipeline, but are not SUMO/Veins
or real-network performance evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

from ml.evaluate_predictors import LabeledWindow, metrics, select_winner
from ml.predictor import PREDICTOR_FACTORIES, create_predictor
from sim.run_experiment import NodeCondition, _features, _update_conditions
from sim.seed_manager import derive_streams, split_seeds, write_manifest


def development_records(seeds: list[int], density: int, rounds: int) -> tuple[list[LabeledWindow], dict[str, list[LabeledWindow]]]:
    """Generate labelled windows using the same feature/condition dynamics as run_experiment.

    A node is labelled reliable only when it is non-Byzantine and its simulated
    next-window behaviour agrees.  The held-out test split is returned but is
    intentionally not scored or used for model selection here.
    """
    split = split_seeds(seeds)
    all_records: list[LabeledWindow] = []
    by_split: dict[str, list[LabeledWindow]] = {"train": [], "validation": [], "test": []}
    allocation = {seed: name for name in by_split for seed in getattr(split, name)}
    for seed in seeds:
        streams, split_name = derive_streams(seed), allocation[seed]
        initial, channel, mobility, behaviour = random.Random(seed), random.Random(streams["channel"]), random.Random(streams["mobility"]), random.Random(streams["traffic"])
        node_ids, f = [f"cav-{index:03d}" for index in range(density)], max(1, (density - 1) // 6)
        malicious = set(random.Random(streams["attack"]).sample(node_ids, min(f, len(node_ids) // 4)))
        conditions = {node: NodeCondition(initial.uniform(.62, .98), node in malicious) for node in node_ids}
        for round_id in range(rounds):
            congestion = min(.95, max(.05, density / 350 + .23 * (1 + math.sin(round_id / 17)) / 2 + channel.uniform(-.08, .08)))
            for node in node_ids:
                feature = _features(channel, conditions[node], congestion)
                reliable = not conditions[node].malicious and behaviour.random() < conditions[node].reliability
                record = LabeledWindow(split_name, feature, reliable)
                all_records.append(record); by_split[split_name].append(record)
            _update_conditions(mobility, conditions, congestion)
    return all_records, by_split


def _roc(labels: list[bool], probabilities: list[float]) -> tuple[list[float], list[float]]:
    thresholds = sorted(set(probabilities), reverse=True)
    positives, negatives = sum(labels), len(labels) - sum(labels)
    fpr, tpr = [0.0], [0.0]
    for threshold in thresholds:
        tp = sum(label and score >= threshold for label, score in zip(labels, probabilities))
        fp = sum(not label and score >= threshold for label, score in zip(labels, probabilities))
        tpr.append(tp / positives if positives else 0.0); fpr.append(fp / negatives if negatives else 0.0)
    return [*fpr, 1.0], [*tpr, 1.0]


def _even_sample(records: list[LabeledWindow], maximum: int) -> list[LabeledWindow]:
    """Bound tree/forest fitting cost while retaining coverage across the split."""
    if len(records) <= maximum: return records
    step = len(records) / maximum
    return [records[int(index * step)] for index in range(maximum)]


def _display_name(name: str) -> str:
    return {"logistic_regression": "Logistic regression", "decision_tree": "Decision tree", "random_forest": "Random forest", "mlp": "MLP"}[name]


def generate(output: Path, seed_start: int = 1001, total_seeds: int = 30, density: int = 30, rounds: int = 40) -> tuple[Path, Path, Path, Path]:
    if total_seeds < 15: raise ValueError("use at least 15 seeds to preserve non-empty train/validation/test splits")
    seeds, split = list(range(seed_start, seed_start + total_seeds)), split_seeds(list(range(seed_start, seed_start + total_seeds)))
    _, records = development_records(seeds, density, rounds)
    training, validation = _even_sample(records["train"], 256), _even_sample(records["validation"], 512)
    labels = [record.reliable for record in validation]
    predictions: dict[str, list[float]] = {}
    report: dict[str, object] = {}
    for name in PREDICTOR_FACTORIES:
        predictor = create_predictor(name)
        for record in training: predictor.update(record.features, record.reliable)
        probabilities = [predictor.predict(record.features) for record in validation]
        predictions[name] = probabilities; report[name] = metrics(labels, probabilities)
    winner = select_winner(report)  # type: ignore[arg-type]
    output.mkdir(parents=True, exist_ok=True); write_manifest(output / "seed_manifest.csv", split)
    summary = output / "ml_validation_metrics.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        fields = ["model", "precision", "recall", "accuracy", "f1", "auroc", "true_positive", "false_positive", "false_negative", "true_negative"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for name, value in report.items(): writer.writerow({"model": name, **value.__dict__})
    (output / "study_manifest.json").write_text(json.dumps({"study_type": "controlled-development-model-not-veins", "density": density, "rounds_per_seed": rounds, "seed_split": {name: list(getattr(split, name)) for name in ("train", "validation", "test")}, "training_windows_sampled": len(training), "validation_windows_sampled": len(validation), "selection_split": "validation", "held_out_test_used": False, "winner": winner, "warning": "Figures are generated from the deterministic development harness, not SUMO/Veins/OMNeT++ measurements."}, indent=2), encoding="utf-8")

    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    colors = {"logistic_regression": "#1f77b4", "decision_tree": "#ff7f0e", "random_forest": "#2ca02c", "mlp": "#d62728"}
    roc_path = output / "ml_algorithm_auroc.png"
    fig, axis = plt.subplots(figsize=(5.2, 4.1), constrained_layout=True)
    for name, probabilities in predictions.items():
        fpr, tpr = _roc(labels, probabilities)
        axis.plot(fpr, tpr, linewidth=2, color=colors[name], label=f"{_display_name(name)} (AUROC={report[name].auroc:.3f})")
    axis.plot([0, 1], [0, 1], "--", color="#666666", linewidth=1, label="Random classifier")
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="False-positive rate (unreliable node trusted)", ylabel="True-positive rate (reliable node selected)", title="Validation ROC comparison of reliability predictors")
    axis.grid(alpha=.22); axis.legend(loc="lower right", frameon=False, fontsize=7.5)
    fig.text(.5, -.02, "Controlled development harness; validation seeds only. Not a SUMO/Veins result.", ha="center", fontsize=7.5)
    fig.savefig(roc_path, dpi=300, bbox_inches="tight"); plt.close(fig)

    # Paper-ready single asset: ROC plus all five required validation metrics.
    comparison_png, comparison_pdf = output / "ml_predictor_comparison.png", output / "ml_predictor_comparison.pdf"
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.7), gridspec_kw={"width_ratios": [1.25, 1]}, constrained_layout=True)
    axis = axes[0]
    for name, probabilities in predictions.items():
        fpr, tpr = _roc(labels, probabilities)
        axis.plot(fpr, tpr, linewidth=1.8, color=colors[name], label=f"{_display_name(name)} ({report[name].auroc:.3f})")
    axis.plot([0, 1], [0, 1], "--", color="#666666", linewidth=1, label="Random")
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="False-positive rate", ylabel="True-positive rate", title="(a) Validation ROC curves")
    axis.grid(alpha=.22); axis.legend(loc="lower right", frameon=False, fontsize=7)
    metric_names = ("precision", "recall", "accuracy", "f1", "auroc")
    table_axis = axes[1]; table_axis.axis("off"); table_axis.set_title("(b) Validation metrics", pad=10)
    rows = [[_display_name(name), *(f"{getattr(report[name], metric):.3f}" for metric in metric_names)] for name in PREDICTOR_FACTORIES]
    table = table_axis.table(cellText=rows, colLabels=["Model", "Precision", "Recall", "Accuracy", "F1", "AUROC"], loc="center", cellLoc="center", colLoc="center", colWidths=[.31, .14, .13, .15, .11, .14])
    table.auto_set_font_size(False); table.set_fontsize(7.6); table.scale(1.0, 1.55)
    for column, metric in enumerate(metric_names, start=1):
        maximum = max(getattr(value, metric) for value in report.values())
        for row_index, name in enumerate(PREDICTOR_FACTORIES, start=1):
            if getattr(report[name], metric) == maximum: table[(row_index, column)].get_text().set_weight("bold")
    fig.text(.5, -.02, "Controlled development harness; validation seeds only. Not a SUMO/Veins result.", ha="center", fontsize=7.5)
    fig.savefig(comparison_png, dpi=300, bbox_inches="tight"); fig.savefig(comparison_pdf, bbox_inches="tight"); plt.close(fig)

    result = report[winner]
    matrix = [[result.true_negative, result.false_positive], [result.false_negative, result.true_positive]]
    cm_path = output / "ml_winner_confusion_matrix.png"
    fig, axis = plt.subplots(figsize=(4.8, 4.1), constrained_layout=True)
    image = axis.imshow(matrix, cmap="Blues")
    for row in range(2):
        for column in range(2): axis.text(column, row, str(matrix[row][column]), ha="center", va="center", fontsize=13, fontweight="medium", color="white" if matrix[row][column] > max(map(max, matrix)) / 2 else "black")
    axis.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Predicted\nunreliable", "Predicted\nreliable"], yticklabels=["Actually\nunreliable", "Actually\nreliable"], xlabel="Model prediction", ylabel="Observed reliability", title=f"Validation confusion matrix: {_display_name(winner)}")
    fig.colorbar(image, ax=axis, fraction=.046, pad=.04, label="Window count")
    fig.text(.5, -.02, "Controlled development harness; validation seeds only. Not a SUMO/Veins result.", ha="center", fontsize=7.5)
    fig.savefig(cm_path, dpi=300, bbox_inches="tight"); plt.close(fig)
    return summary, comparison_png, comparison_pdf, cm_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate development-harness ML validation figures.")
    parser.add_argument("--output", type=Path, required=True); parser.add_argument("--seed-start", type=int, default=1001)
    parser.add_argument("--total-seeds", type=int, default=30); parser.add_argument("--density", type=int, default=30); parser.add_argument("--rounds", type=int, default=40)
    args = parser.parse_args(); print(*generate(args.output, args.seed_start, args.total_seeds, args.density, args.rounds), sep="\n")


if __name__ == "__main__": main()
