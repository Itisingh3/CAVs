import unittest
from sim.generate_cav_telemetry import generate_scenario
from ml.train_temporal_pipeline import FEATURE_COLUMNS

class CAVTelemetryTests(unittest.TestCase):
    def test_generated_windows_are_canonical_and_causal(self):
        rows = generate_scenario(42, 4, 6)
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(set(FEATURE_COLUMNS).issubset(row) and row["credential_trust"] == 1.0 for row in rows))
        self.assertTrue(all("session_key" not in row and "shared_secret" not in row for row in rows))
        by_node = [row for row in rows if row["node_id"] == "cav-000"]
        self.assertEqual([row["window_index"] for row in by_node], [0, 1, 2, 3])
