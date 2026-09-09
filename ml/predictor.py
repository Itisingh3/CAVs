"""Small, dependency-free reliability predictors used by the grouping policy.

All models expose the same online ``predict``/``update`` contract. The tree,
forest, and MLP are deliberately bounded CPU-only models.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from ml.features import NodeFeatures


class ReliabilityPredictor(Protocol):
    observations: int
    def predict(self, features: NodeFeatures) -> float: ...
    def update(self, features: NodeFeatures, reliable: bool) -> float: ...


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


@dataclass
class OnlineLogisticReliability:
    """Incremental linear baseline; no stored training data."""
    learning_rate: float = 0.15
    l2: float = 0.001
    weights: list[float] = field(default_factory=lambda: [0.0] * 7)
    observations: int = 0

    def predict(self, features: NodeFeatures) -> float:
        return _sigmoid(sum(w * v for w, v in zip(self.weights, [1.0, *features.as_vector()])))

    def update(self, features: NodeFeatures, reliable: bool) -> float:
        x, predicted, label = [1.0, *features.as_vector()], self.predict(features), float(reliable)
        for index in range(len(self.weights)):
            regularizer = self.l2 * self.weights[index] if index else 0.0
            self.weights[index] -= self.learning_rate * ((predicted - label) * x[index] + regularizer)
        self.observations += 1
        return predicted


@dataclass
class _TreeNode:
    probability: float
    feature: int | None = None
    threshold: float = 0.0
    left: "_TreeNode | None" = None
    right: "_TreeNode | None" = None

    def predict(self, values: list[float]) -> float:
        if self.feature is None: return self.probability
        child = self.left if values[self.feature] <= self.threshold else self.right
        return child.predict(values) if child else self.probability


def _gini(rows: list[tuple[list[float], bool]]) -> float:
    if not rows: return 0.0
    p = sum(label for _, label in rows) / len(rows)
    return 2 * p * (1 - p)


def _fit_tree(rows: list[tuple[list[float], bool]], depth: int, max_depth: int, min_leaf: int, features: tuple[int, ...]) -> _TreeNode:
    probability = (sum(label for _, label in rows) + 1) / (len(rows) + 2)
    if depth >= max_depth or len(rows) < min_leaf * 2: return _TreeNode(probability)
    best = None
    parent = _gini(rows)
    for feature in features:
        values = sorted({x[feature] for x, _ in rows})
        for low, high in zip(values, values[1:]):
            threshold = (low + high) / 2
            left, right = [row for row in rows if row[0][feature] <= threshold], [row for row in rows if row[0][feature] > threshold]
            if len(left) < min_leaf or len(right) < min_leaf: continue
            gain = parent - (len(left) * _gini(left) + len(right) * _gini(right)) / len(rows)
            if best is None or gain > best[0]: best = gain, feature, threshold, left, right
    if best is None or best[0] <= 1e-12: return _TreeNode(probability)
    _, feature, threshold, left, right = best
    return _TreeNode(probability, feature, threshold, _fit_tree(left, depth + 1, max_depth, min_leaf, features), _fit_tree(right, depth + 1, max_depth, min_leaf, features))


@dataclass
class DecisionTreeReliability:
    """A shallow, interpretable nonlinear reliability predictor."""
    max_depth: int = 3
    min_samples_leaf: int = 4
    retrain_every: int = 8
    observations: int = 0
    _rows: list[tuple[list[float], bool]] = field(default_factory=list)
    _tree: _TreeNode | None = None

    def predict(self, features: NodeFeatures) -> float:
        return self._tree.predict(features.as_vector()) if self._tree else 0.5

    def update(self, features: NodeFeatures, reliable: bool) -> float:
        predicted = self.predict(features)
        self._rows.append((features.as_vector(), reliable)); self.observations += 1
        if self.observations % self.retrain_every == 0: self._tree = _fit_tree(self._rows, 0, self.max_depth, self.min_samples_leaf, tuple(range(6)))
        return predicted


@dataclass
class RandomForestReliability:
    """Small bagged forest; inference averages a fixed number of shallow trees."""
    trees: int = 9
    max_depth: int = 3
    min_samples_leaf: int = 4
    retrain_every: int = 12
    observations: int = 0
    _rows: list[tuple[list[float], bool]] = field(default_factory=list)
    _forest: list[_TreeNode] = field(default_factory=list)

    def predict(self, features: NodeFeatures) -> float:
        return sum(tree.predict(features.as_vector()) for tree in self._forest) / len(self._forest) if self._forest else 0.5

    def update(self, features: NodeFeatures, reliable: bool) -> float:
        predicted = self.predict(features)
        self._rows.append((features.as_vector(), reliable)); self.observations += 1
        if self.observations % self.retrain_every == 0:
            self._forest = []
            for tree_index in range(self.trees):
                sample = [self._rows[(index * (2 * tree_index + 1) + tree_index) % len(self._rows)] for index in range(len(self._rows))]
                subset = tuple(sorted({(tree_index + offset * 2) % 6 for offset in range(3)}))
                self._forest.append(_fit_tree(sample, 0, self.max_depth, self.min_samples_leaf, subset))
        return predicted


@dataclass
class MLPReliability:
    """Single hidden-layer MLP, the lightweight-complexity upper bound."""
    hidden_units: int = 8
    learning_rate: float = 0.08
    observations: int = 0
    _hidden: list[list[float]] = field(default_factory=list)
    _output: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._hidden:
            self._hidden = [[((unit + 1) * (index + 3) % 11 - 5) / 100 for index in range(7)] for unit in range(self.hidden_units)]
            self._output = [((unit + 2) % 7 - 3) / 100 for unit in range(self.hidden_units + 1)]

    def _forward(self, features: NodeFeatures) -> tuple[list[float], float]:
        x = [1.0, *features.as_vector()]
        hidden = [math.tanh(sum(weight * value for weight, value in zip(row, x))) for row in self._hidden]
        return hidden, _sigmoid(self._output[0] + sum(weight * value for weight, value in zip(self._output[1:], hidden)))

    def predict(self, features: NodeFeatures) -> float: return self._forward(features)[1]

    def update(self, features: NodeFeatures, reliable: bool) -> float:
        x, (hidden, predicted), target = [1.0, *features.as_vector()], self._forward(features), float(reliable)
        error, prior_output = predicted - target, list(self._output)
        self._output[0] -= self.learning_rate * error
        for unit, activation in enumerate(hidden):
            self._output[unit + 1] -= self.learning_rate * error * activation
            delta = error * prior_output[unit + 1] * (1 - activation * activation)
            for index, value in enumerate(x): self._hidden[unit][index] -= self.learning_rate * delta * value
        self.observations += 1
        return predicted


PREDICTOR_FACTORIES = {"logistic_regression": OnlineLogisticReliability, "decision_tree": DecisionTreeReliability, "random_forest": RandomForestReliability, "mlp": MLPReliability}


def create_predictor(name: str) -> ReliabilityPredictor:
    try: return PREDICTOR_FACTORIES[name]()
    except KeyError as exc: raise ValueError(f"unknown predictor {name!r}; choose from {', '.join(PREDICTOR_FACTORIES)}") from exc
