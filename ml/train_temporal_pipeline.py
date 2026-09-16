"""Leakage-safe training of the proposed reliability score.

Usage is intentionally CSV-first.  It does not manufacture CAV/PBFT labels
from an automotive CAN corpus; see ``data/README.md`` for the data boundary.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from ml.evaluate_predictors import PredictorMetrics, metrics, select_winner
from ml.predictor import create_predictor
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence
from ml.sequence_models import SequenceRecord, construct_causal_sequences, train_sequence_model


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
    scenario_id: str = "legacy"
    node_id: str = "legacy"
    window_index: int = 0


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
                # Metadata is mandatory for new datasets.  Legacy CSVs remain
                # readable for existing tests, but cannot establish a real
                # scenario/node-level split by themselves.
                rows.append(Window(
                    row["split"].strip(), TemporalEvidence(*(float(row[name]) for name in FEATURE_COLUMNS)), label,
                    row.get("scenario_id", "legacy").strip() or "legacy",
                    row.get("node_id", "legacy").strip() or "legacy",
                    int(row.get("window_index", len(rows))),
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid canonical window at line {line}") from exc
    if not rows:
        raise ValueError("no windows found")
    invalid = sorted({row.split for row in rows} - {"train", "validation", "test"})
    if invalid:
        raise ValueError(f"unknown split values: {', '.join(invalid)}")
    return rows


def sequence_records(rows: list[Window]) -> list[SequenceRecord]:
    """Convert canonical rows without ever using labels as sequence features."""
    owners: dict[tuple[str, str], str] = {}
    result = []
    for row in rows:
        owner = (row.scenario_id, row.node_id)
        if owner in owners and owners[owner] != row.split:
            raise ValueError(f"trace {owner} appears in both {owners[owner]} and {row.split}; split whole traces, not rows")
        owners[owner] = row.split
        result.append(SequenceRecord(row.split, row.scenario_id, row.node_id, row.window_index, row.evidence, row.reliable))
    return result


def train_temporal_candidate(rows: list[Window], model: str, *, sequence_length: int, epochs: int, batch_size: int, learning_rate: float, patience: int, seed: int, device: str, checkpoint: Path | None = None):
    """Fit one genuine recurrent candidate; test rows are never passed to fit."""
    sequences = construct_causal_sequences(sequence_records(rows), sequence_length)
    train = type(sequences)([x for x, r in zip(sequences.features, sequences.records) if r.split == "train"], [y for y, r in zip(sequences.labels, sequences.records) if r.split == "train"], [r for r in sequences.records if r.split == "train"])
    validation = type(sequences)([x for x, r in zip(sequences.features, sequences.records) if r.split == "validation"], [y for y, r in zip(sequences.labels, sequences.records) if r.split == "validation"], [r for r in sequences.records if r.split == "validation"])
    started = perf_counter()
    trained, history = train_sequence_model(model, train, validation, epochs=epochs, batch_size=batch_size, learning_rate=learning_rate, early_stopping_patience=patience, seed=seed, device=device, checkpoint=checkpoint)
    elapsed = perf_counter() - started
    validation_probability = trained.predict_sequences(validation.features)
    return trained, history, metrics(validation.labels, validation_probability), elapsed, sequences


def _yaml_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("YAML configuration requires PyYAML; install requirements-deep.txt") from exc
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _fit_base(rows: list[Window], name: str):
    predictor = create_predictor(name)
    # The deliberately dependency-free tree implementations are bounded online
    # controls.  Fitting every historical row repeatedly is quadratic and does
    # not scale to an exported telemetry trace, so use a deterministic, evenly
    # spaced reservoir for their final bounded retrain.
    fit_rows = rows
    if name in {"decision_tree", "random_forest"} and len(rows) > 256:
        step = len(rows) / 256
        fit_rows = [rows[min(len(rows) - 1, int(index * step))] for index in range(256)]
        predictor.retrain_every = len(fit_rows)  # type: ignore[attr-defined]
    for row in fit_rows:
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


def train_classical_candidate(rows: list[Window], name: str) -> tuple[object, LearnedReliabilityScore, PredictorMetrics]:
    """Fit one pre-selected classical candidate; test data remains untouched."""
    train, validation = [row for row in rows if row.split == "train"], [row for row in rows if row.split == "validation"]
    if not train or not validation: raise ValueError("non-empty train and validation trace groups are required")
    predictor = _fit_base(train, name)
    probabilities = [predictor.predict(row.evidence.base_features()) for row in validation]
    scorer = LearnedReliabilityScore().fit([(row.evidence, probability, row.reliable) for row, probability in zip(validation, probabilities)])
    return predictor, scorer, metrics([row.reliable for row in validation], probabilities)


def evaluate_locked_test(rows: list[Window], predictor: object, scorer: LearnedReliabilityScore) -> PredictorMetrics:
    test = [row for row in rows if row.split == "test"]
    if not test:
        raise ValueError("locked test split is absent")
    probabilities = [scorer.predict(row.evidence, predictor.predict(row.evidence.base_features())) for row in test]
    return metrics([row.reliable for row in test], probabilities)


def write_report(path: Path, winner: str, comparison: dict[str, PredictorMetrics], scorer: LearnedReliabilityScore, test: PredictorMetrics | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "stage", "model", "precision", "recall", "accuracy", "f1", "auroc", "auprc",
            "true_positive", "false_positive", "false_negative", "true_negative",
            "influence_ml_probability", "influence_history", "influence_consensus", "influence_network",
        ]
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
    parser.add_argument("--model", choices=("logistic_regression", "decision_tree", "random_forest", "mlp", "lstm", "gru", "bilstm"), help="candidate to train; recurrent names use [samples, sequence_length, 10]")
    parser.add_argument("--config", type=Path, default=Path("configs/ml_training.yaml"))
    parser.add_argument("--epochs", type=int); parser.add_argument("--batch-size", type=int)
    parser.add_argument("--learning-rate", type=float); parser.add_argument("--sequence-length", type=int)
    parser.add_argument("--seed", type=int); parser.add_argument("--device")
    parser.add_argument("--evaluate-locked-test", action="store_true", help="explicitly read the untouched test rows once")
    args = parser.parse_args()
    config = _yaml_config(args.config if args.config.exists() else None)
    dataset, training, hardware = config.get("dataset", {}), config.get("training", {}), config.get("hardware", {})
    rows = read_windows(args.input)
    if args.model in {"lstm", "gru", "bilstm"}:
        model, history, validation, elapsed, sequences = train_temporal_candidate(
            rows, args.model, sequence_length=args.sequence_length or dataset.get("sequence_length", 20),
            epochs=args.epochs or training.get("epochs", 50), batch_size=args.batch_size or dataset.get("batch_size", 64),
            learning_rate=args.learning_rate or training.get("learning_rate", .001), patience=training.get("early_stopping_patience", 8),
            seed=args.seed or training.get("random_seed", 42), device=args.device or hardware.get("device", "auto"),
            checkpoint=Path("artifacts/models") / f"{args.model}_best.pt",
        )
        test = None
        if args.evaluate_locked_test:
            test_samples = [x for x, r in zip(sequences.features, sequences.records) if r.split == "test"]
            test_labels = [y for y, r in zip(sequences.labels, sequences.records) if r.split == "test"]
            if not test_samples: raise ValueError("locked test split has no complete sequences")
            test = metrics(test_labels, model.predict_sequences(test_samples))
        write_report(args.output, args.model, {args.model: validation}, LearnedReliabilityScore(), test)
        print(f"validation_model={args.model}\nsequence_shape=[samples, {args.sequence_length or dataset.get('sequence_length', 20)}, 10]\ntraining_seconds={elapsed:.3f}\nparameters={model.parameter_count}\nreport={args.output}")
        return
    if args.model in {"logistic_regression", "decision_tree", "random_forest", "mlp"}:
        predictor, scorer, validation = train_classical_candidate(rows, args.model)
        test = evaluate_locked_test(rows, predictor, scorer) if args.evaluate_locked_test else None
        write_report(args.output, args.model, {args.model: validation}, scorer, test)
        print(f"validation_model={args.model}\nreport={args.output}")
        return
    winner, predictor, scorer, comparison = train_and_select(rows)
    test = evaluate_locked_test(rows, predictor, scorer) if args.evaluate_locked_test else None
    write_report(args.output, winner, comparison, scorer, test)
    print(f"validation_winner={winner}")
    print("learned_influence=" + ", ".join(f"{name}={value:.3f}" for name, value in scorer.normalized_influence().items()))
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
