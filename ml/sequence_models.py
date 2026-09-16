"""Causal sequence construction and optional PyTorch reliability models.

These models are deliberately separate from :mod:`ml.predictor`: the latter
is a bounded, single-window online interface used by the existing consensus
code.  Recurrent models consume a *history* of ten CAV telemetry features and
are trained/evaluated offline before a deployment adapter is introduced.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from ml.temporal_reliability import TemporalEvidence

SequenceModelName = Literal["lstm", "gru", "bilstm"]


@dataclass(frozen=True)
class SequenceRecord:
    """A labelled causal observation belonging to one node/session trace."""

    split: str
    scenario_id: str
    node_id: str
    window_index: int
    evidence: TemporalEvidence
    reliable: bool


@dataclass(frozen=True)
class SequenceDataset:
    """Features have the explicit shape ``[samples, sequence_length, 10]``."""

    features: list[list[list[float]]]
    labels: list[bool]
    records: list[SequenceRecord]


def construct_causal_sequences(records: Iterable[SequenceRecord], sequence_length: int) -> SequenceDataset:
    """Construct ``X(t-K+1), ..., X(t) -> y(t)`` without cross-trace leakage.

    A sequence is never allowed to cross a split, scenario, or node boundary.
    The target is the final observation, so no value after the decision time is
    available to the model.
    """
    if sequence_length < 1:
        raise ValueError("sequence_length must be positive")
    groups: dict[tuple[str, str, str], list[SequenceRecord]] = {}
    for record in records:
        groups.setdefault((record.split, record.scenario_id, record.node_id), []).append(record)
    features: list[list[list[float]]] = []
    labels: list[bool] = []
    targets: list[SequenceRecord] = []
    for key in sorted(groups):
        trace = sorted(groups[key], key=lambda item: item.window_index)
        if len({item.window_index for item in trace}) != len(trace):
            raise ValueError(f"duplicate window_index in trace {key}")
        for end in range(sequence_length - 1, len(trace)):
            window = trace[end - sequence_length + 1 : end + 1]
            features.append([item.evidence.as_vector() for item in window])
            labels.append(trace[end].reliable)
            targets.append(trace[end])
    return SequenceDataset(features, labels, targets)


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:  # Base package intentionally remains CPU-light.
        raise RuntimeError("deep sequence models require PyTorch; install requirements-deep.txt") from exc
    return torch, nn


@dataclass
class TrainedSequenceModel:
    name: SequenceModelName
    model: object
    device: str
    parameter_count: int

    def predict_sequences(self, sequences: list[list[list[float]]]) -> list[float]:
        """Return ``P(reliable | X(t-K+1:t))`` for causal, complete windows."""
        if not sequences:
            return []
        torch, _ = _torch()
        self.model.eval()
        with torch.no_grad():
            data = torch.tensor(sequences, dtype=torch.float32, device=self.device)
            return self.model(data).squeeze(1).cpu().tolist()


def train_sequence_model(
    name: SequenceModelName,
    train: SequenceDataset,
    validation: SequenceDataset,
    *,
    epochs: int = 50,
    batch_size: int = 64,
    learning_rate: float = 0.001,
    early_stopping_patience: int = 8,
    seed: int = 42,
    device: str = "auto",
    checkpoint: Path | None = None,
) -> tuple[TrainedSequenceModel, dict[str, list[float]]]:
    """Train LSTM/GRU/BiLSTM on locked, causal sequence sets.

    Validation loss controls early stopping.  Callers must not pass test data
    here; its sole use is final evaluation after selection.
    """
    if name not in {"lstm", "gru", "bilstm"}:
        raise ValueError("model must be lstm, gru, or bilstm")
    if not train.features or not validation.features:
        raise ValueError("train and validation must each contain complete sequences")
    if any(len(sequence) != len(train.features[0]) or any(len(row) != 10 for row in sequence) for sequence in train.features + validation.features):
        raise ValueError("sequence tensors must have shape [samples, sequence_length, 10]")
    torch, nn = _torch()
    random.seed(seed); torch.manual_seed(seed)
    resolved_device = "cuda" if device == "auto" and torch.cuda.is_available() else ("cpu" if device == "auto" else device)
    if resolved_device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")

    class RecurrentClassifier(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            recurrent = nn.GRU if name == "gru" else nn.LSTM
            self.recurrent = recurrent(10, 32, batch_first=True, bidirectional=name == "bilstm")
            self.dropout = nn.Dropout(0.2)
            self.output = nn.Linear(64 if name == "bilstm" else 32, 1)
        def forward(self, inputs):
            output, _ = self.recurrent(inputs)
            return torch.sigmoid(self.output(self.dropout(output[:, -1, :])))

    model = RecurrentClassifier().to(resolved_device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.BCELoss()
    x_train = torch.tensor(train.features, dtype=torch.float32)
    y_train = torch.tensor(train.labels, dtype=torch.float32).unsqueeze(1)
    x_valid = torch.tensor(validation.features, dtype=torch.float32, device=resolved_device)
    y_valid = torch.tensor(validation.labels, dtype=torch.float32, device=resolved_device).unsqueeze(1)
    history = {"train_loss": [], "validation_loss": [], "train_accuracy": [], "validation_accuracy": []}
    best_loss, remaining, best_state = float("inf"), early_stopping_patience, None
    for _ in range(epochs):
        model.train(); total_loss = 0.0; correct = 0
        ordering = torch.randperm(len(x_train))
        for start in range(0, len(x_train), batch_size):
            indices = ordering[start : start + batch_size]
            xb, yb = x_train[indices].to(resolved_device), y_train[indices].to(resolved_device)
            optimizer.zero_grad(); probabilities = model(xb); loss = criterion(probabilities, yb)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * len(indices); correct += ((probabilities >= .5) == yb.bool()).sum().item()
        model.eval()
        with torch.no_grad():
            valid_probabilities = model(x_valid); valid_loss = criterion(valid_probabilities, y_valid).item()
            valid_accuracy = ((valid_probabilities >= .5) == y_valid.bool()).float().mean().item()
        history["train_loss"].append(total_loss / len(x_train)); history["train_accuracy"].append(correct / len(x_train))
        history["validation_loss"].append(valid_loss); history["validation_accuracy"].append(valid_accuracy)
        if valid_loss < best_loss:
            best_loss, remaining = valid_loss, early_stopping_patience
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            if checkpoint:
                checkpoint.parent.mkdir(parents=True, exist_ok=True); torch.save(best_state, checkpoint)
        else:
            remaining -= 1
            if remaining <= 0: break
    if best_state is not None: model.load_state_dict(best_state)
    return TrainedSequenceModel(name, model, resolved_device, sum(item.numel() for item in model.parameters())), history
