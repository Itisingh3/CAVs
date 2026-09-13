"""Leakage-safe training of the proposed reliability score.

Usage is intentionally CSV-first.  It does not manufacture CAV/PBFT labels
from an automotive CAN corpus; see ``data/README.md`` for the data boundary.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from ml.evaluate_predictors import PredictorMetrics, metrics, select_winner
from ml.predictor import create_predictor
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence


FEATURE_COLUMNS = (
    "agreement_rate", "normalized_rtt", "pdr", "link_quality", "score_trend",
    "recent_fault_rate", "velocity_stability", "consensus_participation",
    "historical_reputation", "credential_trust",
)


@dataclass(frozen=True)
class Window:
    split: str
    evidence: TemporalEvidence
    reliable: bool


def read_windows(path: Path) -> list[Window]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = {"split", "reliable", *FEATURE_COLUMNS}
        if not reader.fieldnames or not expected.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain: {', '.join(sorted(expected))}")
        rows = []
        for line, row in enumerate(reader, start=2):
            try:
                label = row["reliable"].strip().lower() in {"1", "true", "yes"}
                rows.append(Window(row["split"].strip(), TemporalEvidence(*(float(row[name]) for name in FEATURE_COLUMNS)), label))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid canonical window at line {line}") from exc
    if not rows:
        raise ValueError("no windows found")
    invalid = sorted({row.split for row in rows} - {"train", "validation", "test"})
    if invalid:
        raise ValueError(f"unknown split values: {', '.join(invalid)}")
    return rows


def _fit_base(rows: list[Window], name: str):
    predictor = create_predictor(name)
    for row in rows:
        predictor.update(row.evidence.base_features(), row.reliable)
    return predictor


def train_and_select(rows: list[Window]) -> tuple[str, object, LearnedReliabilityScore, dict[str, PredictorMetrics]]:
    train = [row for row in rows if row.split == "train"]
    validation = [row for row in rows if row.split == "validation"]
    if not train or not validation:
        raise ValueError("non-empty train and validation trace groups are required")
    comparison: dict[str, PredictorMetrics] = {}
    for name in ("logistic_regression", "decision_tree", "random_forest", "mlp"):
        candidate = _fit_base(train, name)
        probabilities = [candidate.predict(row.evidence.base_features()) for row in validation]
        comparison[name] = metrics([row.reliable for row in validation], probabilities)
    winner = select_winner(comparison)
    predictor = _fit_base(train, winner)
    calibration_rows = [
        (row.evidence, predictor.predict(row.evidence.base_features()), row.reliable)
        for row in validation
    ]
    scorer = LearnedReliabilityScore().fit(calibration_rows)
    return winner, predictor, scorer, comparison


def evaluate_locked_test(rows: list[Window], predictor: object, scorer: LearnedReliabilityScore) -> PredictorMetrics:
    test = [row for row in rows if row.split == "test"]
    if not test:
        raise ValueError("locked test split is absent")
    probabilities = [scorer.predict(row.evidence, predictor.predict(row.evidence.base_features())) for row in test]
    return metrics([row.reliable for row in test], probabilities)


def write_report(path: Path, winner: str, comparison: dict[str, PredictorMetrics], scorer: LearnedReliabilityScore, test: PredictorMetrics | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["stage", "model", "precision", "recall", "accuracy", "f1", "auroc", "auprc", "influence_ml_probability", "influence_history", "influence_consensus", "influence_network"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        influence = {f"influence_{key}": value for key, value in scorer.normalized_influence().items()}
        for model, value in comparison.items():
            writer.writerow({"stage": "validation", "model": model, **value.__dict__})
        if test is not None:
            writer.writerow({"stage": "locked_test", "model": winner, **test.__dict__, **influence})


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a causal, learned four-evidence reliability score.")
    parser.add_argument("input", type=Path, help="canonical CSV described in data/README.md")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluate-locked-test", action="store_true", help="explicitly read the untouched test rows once")
    args = parser.parse_args()
    rows = read_windows(args.input)
    winner, predictor, scorer, comparison = train_and_select(rows)
    test = evaluate_locked_test(rows, predictor, scorer) if args.evaluate_locked_test else None
    write_report(args.output, winner, comparison, scorer, test)
    print(f"validation_winner={winner}")
    print("learned_influence=" + ", ".join(f"{name}={value:.3f}" for name, value in scorer.normalized_influence().items()))
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
