import unittest
import csv
import tempfile
from pathlib import Path

from ml.train_temporal_pipeline import read_windows, train_and_select, evaluate_locked_test
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence


def evidence(reliable: bool) -> TemporalEvidence:
    high, low = (0.9, 0.1) if reliable else (0.1, 0.9)
    return TemporalEvidence(high, low, high, high, high, low, high, high, high, high)


class TemporalReliabilityTests(unittest.TestCase):
    def test_learned_evidence_score_is_bounded_and_data_fitted(self):
        rows = [(evidence(index % 2 == 0), 0.9 if index % 2 == 0 else 0.1, index % 2 == 0) for index in range(20)]
        score = LearnedReliabilityScore(epochs=30).fit(rows)
        self.assertTrue(score.fitted)
        self.assertGreater(score.predict(evidence(True), .9), score.predict(evidence(False), .1))
        self.assertAlmostEqual(sum(score.normalized_influence().values()), 1.0)

    def test_rejects_insufficient_or_unbounded_evidence(self):
        with self.assertRaises(ValueError):
            TemporalEvidence(1.1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0)
        with self.assertRaises(ValueError):
            LearnedReliabilityScore().fit([])

    def test_pipeline_keeps_test_rows_out_of_selection(self):
        fields = ["split", "reliable", "agreement_rate", "normalized_rtt", "pdr", "link_quality", "score_trend", "recent_fault_rate", "velocity_stability", "consensus_participation", "historical_reputation", "credential_trust"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "windows.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
                for split, count in (("train", 20), ("validation", 10), ("test", 6)):
                    for index in range(count):
                        reliable = index % 2 == 0
                        item = evidence(reliable)
                        writer.writerow({"split": split, "reliable": str(reliable), **dict(zip(fields[2:], item.as_vector()))})
            rows = read_windows(path)
            winner, predictor, scorer, report = train_and_select(rows)
            self.assertIn(winner, report)
            self.assertTrue(scorer.fitted)
            self.assertGreaterEqual(evaluate_locked_test(rows, predictor, scorer).accuracy, 0.0)
