"""Parameter-grid generator; execute each emitted config with paired seed lists."""
from itertools import product


def static_configurations():
    for penalty, threshold, window in product((3.0, 5.0, 10.0), (0.5, 1.0, 2.0), (25, 50, 100)):
        yield {"agreement_delta": 1.0, "disagreement_delta": -penalty, "threshold_multiplier": threshold, "reassignment_window": window}
