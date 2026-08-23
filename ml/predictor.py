from __future__ import annotations

import math
from dataclasses import dataclass, field

from ml.features import NodeFeatures


@dataclass
class OnlineLogisticReliability:
    learning_rate: float = 0.15
    l2: float = 0.001
    weights: list[float] = field(default_factory=lambda: [0.0] * 7)  # intercept + six features
    observations: int = 0

    def predict(self, features: NodeFeatures) -> float:
        x = [1.0, *features.as_vector()]
        z = max(-30.0, min(30.0, sum(w * v for w, v in zip(self.weights, x))))
        return 1.0 / (1.0 + math.exp(-z))

    def update(self, features: NodeFeatures, reliable: bool) -> float:
        x, predicted, label = [1.0, *features.as_vector()], self.predict(features), 1.0 if reliable else 0.0
        for index in range(len(self.weights)):
            regularizer = self.l2 * self.weights[index] if index else 0.0
            self.weights[index] -= self.learning_rate * ((predicted - label) * x[index] + regularizer)
        self.observations += 1
        return predicted
