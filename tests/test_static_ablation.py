import json
import tempfile
import unittest
from pathlib import Path
from sim.run_static_ablation import sweep

class StaticAblationTests(unittest.TestCase):
    def test_validation_selection_writes_explicit_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            locked = sweep(Path(directory), density=7, seeds=[1], rounds=3, warmup_rounds=1)
            saved = json.loads((Path(directory) / "static_config_lock.json").read_text(encoding="utf-8"))
        self.assertEqual(locked["winner"], saved["winner"])
        self.assertEqual(saved["selection_split"], "development_validation_only")
