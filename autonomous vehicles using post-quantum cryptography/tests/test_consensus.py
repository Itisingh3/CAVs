import unittest

from consensus.ags_pbft_baseline import AGSConfig, AGSPBFTBaseline
from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from ml.features import NodeFeatures


class ConsensusTests(unittest.TestCase):
    def setUp(self): self.ids = [f"n{index}" for index in range(7)]
    def test_baseline_defaults_and_reassignment(self):
        engine = AGSPBFTBaseline(self.ids, 2, AGSConfig(reassignment_window=1, consensus_fraction=0.5))
        engine.record_round({"n0", "n1", "n2", "n3", "n4"}, "1")
        self.assertEqual(engine.nodes["n0"].score, 101.0); self.assertEqual(engine.nodes["n6"].score, 95.0)
        self.assertGreaterEqual(len(engine.consensus_ids()), 7)
        self.assertTrue(any(event["event"] == "reassignment" for event in engine.events))
    def test_ml_guard_falls_back_without_labels(self):
        engine = MLAdaptiveAGSPBFT(self.ids, 2, AGSConfig(reassignment_window=1))
        features = {node: NodeFeatures(.8,.2,.9,.9,.7,.1) for node in self.ids}
        engine.record_round(set(self.ids), "1")
        self.assertFalse(any(event["event"] == "reassignment" for event in engine.events))
        engine.reassign_with_features("1", features, .4)
        self.assertTrue(any(event["event"] == "ml_fallback" for event in engine.events))
