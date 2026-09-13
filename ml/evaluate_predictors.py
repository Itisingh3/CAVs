"""Offline train/validation comparison for reliability predictors.

Input is CSV generated from logged windows, with a pre-assigned ``split`` and
``reliable`` label. This command refuses test records so test seeds remain
untouched until the already-selected model is evaluated in the simulator.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from ml.features import NodeFeatures
from ml.predictor import PREDICTOR_FACTORIES, ReliabilityPredictor, create_predictor

FEATURE_COLUMNS = ("agreement_rate", "normalized_rtt", "pdr", "link_quality", "score_trend", "recent_fault_rate")


@dataclass(frozen=True)
class LabeledWindow:
    split: str
    features: NodeFeatures
    reliable: bool


@dataclass(frozen=True)
class PredictorMetrics:
    precision: float
    recall: float
    accuracy: float
    f1: float
    auroc: float
    auprc: float
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int


def metrics(labels: list[bool], probabilities: list[float], threshold: float = 0.5) -> PredictorMetrics:
    if len(labels) != len(probabilities) or not labels: raise ValueError("labels and probabilities must be non-empty and aligned")
    tp = sum(label and score >= threshold for label, score in zip(labels, probabilities))
    fp = sum(not label and score >= threshold for label, score in zip(labels, probabilities))
    fn = sum(label and score < threshold for label, score in zip(labels, probabilities))
    tn = len(labels) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    accuracy = (tp + tn) / len(labels)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    positives, negatives = [score for label, score in zip(labels, probabilities) if label], [score for label, score in zip(labels, probabilities) if not label]
    # Mann-Whitney formulation, including half credit for ties.
    auroc = sum((positive > negative) + 0.5 * (positive == negative) for positive in positives for negative in negatives) / (len(positives) * len(negatives)) if positives and negatives else float("nan")
    # Average precision is the area under the step-wise precision-recall
    # curve.  Unlike accuracy it remains informative for rare unreliable nodes.
    positives_total = sum(labels)
    ranked = sorted(zip(probabilities, labels), reverse=True)
    found_positive, prior_recall, auprc = 0, 0.0, 0.0
    for rank, (_, label) in enumerate(ranked, start=1):
        if label:
            found_positive += 1
            recall_at_rank = found_positive / positives_total
            auprc += (found_positive / rank) * (recall_at_rank - prior_recall)
            prior_recall = recall_at_rank
    return PredictorMetrics(precision, recall, accuracy, f1, auroc, auprc, tp, fp, fn, tn)


def train_and_validate(records: list[LabeledWindow]) -> dict[str, PredictorMetrics]:
    training, validation = [row for row in records if row.split == "train"], [row for row in records if row.split == "validation"]
    if not training or not validation: raise ValueError("records must contain non-empty train and validation splits")
    if any(row.split not in {"train", "validation"} for row in records): raise ValueError("offline selection accepts train/validation rows only; test is protected")
    result = {}
    for name in PREDICTOR_FACTORIES:
        predictor: ReliabilityPredictor = create_predictor(name)
        for row in training: predictor.update(row.features, row.reliable)
        probabilities = [predictor.predict(row.features) for row in validation]
        result[name] = metrics([row.reliable for row in validation], probabilities)
    return result


def select_winner(results: dict[str, PredictorMetrics]) -> str:
    if not results: raise ValueError("no predictor results")
    # AUROC can be undefined if validation has one class; deterministic name ties preserve reproducibility.
    return max(sorted(results), key=lambda name: (results[name].f1, -1.0 if results[name].auroc != results[name].auroc else results[name].auroc))


def read_records(path: Path) -> list[LabeledWindow]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = {"split", "reliable", *FEATURE_COLUMNS}
        if not reader.fieldnames or not expected.issubset(reader.fieldnames): raise ValueError(f"{path} must contain {', '.join(sorted(expected))}")
        return [LabeledWindow(row["split"], NodeFeatures(*(float(row[column]) for column in FEATURE_COLUMNS)), row["reliable"].strip().lower() in {"1", "true", "yes"}) for row in reader]


def write_report(path: Path, results: dict[str, PredictorMetrics]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["model", "precision", "recall", "accuracy", "f1", "auroc", "auprc", "true_positive", "false_positive", "false_negative", "true_negative"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for name, value in results.items(): writer.writerow({"model": name, **value.__dict__})
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare reliability predictors on pre-registered train/validation windows.")
    parser.add_argument("input", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = train_and_validate(read_records(args.input)); write_report(args.output, results)
    print(f"winner={select_winner(results)}\nreport={args.output}")


if __name__ == "__main__": main()
