import tempfile
import unittest
from pathlib import Path
from data.preprocess_road import read_raw_log, read_signal_csv, scenario_split, window_capture

class RoadPreprocessingTests(unittest.TestCase):
    def test_causal_windows_keep_road_labels_separate_from_features(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.csv"; path.write_text("Label,Time,ID,A\n0,0.0,1,1\n0,0.2,1,2\n1,1.1,2,\n", encoding="utf-8")
            rows = window_capture(read_signal_csv(path), "ambient/example", window_seconds=1.0)
        self.assertEqual([row["intrusion"] for row in rows], [0, 1])
        self.assertTrue(all("credential_trust" not in row and "frame_count" in row for row in rows))
        self.assertEqual({row["split"] for row in rows}, {scenario_split("ambient/example")})

    def test_raw_can_fallback_parses_payload_without_cav_features(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attack.log"; path.write_text("(10.0) can0 123#00FF\n(10.2) can0 124#10\n", encoding="utf-8")
            rows = window_capture(read_raw_log(path, intrusion=True), "attacks/example", window_seconds=1.0)
        self.assertEqual(rows[0]["intrusion"], 1)
        self.assertEqual(rows[0]["frame_count"], 2.0)
