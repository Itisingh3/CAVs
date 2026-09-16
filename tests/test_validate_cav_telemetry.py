import tempfile
import unittest
from pathlib import Path
from data.validate_cav_telemetry import validate
from sim.generate_cav_telemetry import generate

class ValidateCAVTelemetryTests(unittest.TestCase):
    def test_generated_schema_is_valid_for_development_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cav.csv"; generate(path, scenarios=24, rounds=2, density=4)
            report = validate(path)
        self.assertEqual(report["traces"], 96)
