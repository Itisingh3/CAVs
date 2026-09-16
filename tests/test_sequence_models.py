import unittest

from ml.sequence_models import SequenceRecord, construct_causal_sequences
from ml.temporal_reliability import TemporalEvidence


def record(split: str, scenario: str, node: str, index: int, reliable: bool = True) -> SequenceRecord:
    value = .9 if reliable else .1
    return SequenceRecord(split, scenario, node, index, TemporalEvidence(value, 1-value, value, value, value, 1-value, value, value, value, value), reliable)


class SequenceConstructionTests(unittest.TestCase):
    def test_builds_real_causal_ten_feature_tensors(self):
        data = construct_causal_sequences([record("train", "s1", "n1", index) for index in range(5)], 3)
        self.assertEqual(len(data.features), 3)
        self.assertEqual((len(data.features[0]), len(data.features[0][0])), (3, 10))
        self.assertEqual(data.records[0].window_index, 2)

    def test_never_crosses_node_or_split_boundaries(self):
        records = [*(record("train", "s1", "n1", index) for index in range(2)), *(record("train", "s1", "n2", index) for index in range(2)), *(record("validation", "s2", "n1", index) for index in range(3))]
        data = construct_causal_sequences(records, 3)
        self.assertEqual(len(data.features), 1)
        self.assertEqual(data.records[0].split, "validation")

    def test_rejects_duplicate_decision_times(self):
        with self.assertRaises(ValueError):
            construct_causal_sequences([record("train", "s1", "n1", 1), record("train", "s1", "n1", 1)], 1)
