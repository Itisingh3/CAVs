import unittest

from ml.evaluate_predictors import LabeledWindow, select_winner, train_and_validate
from ml.features import NodeFeatures
from ml.predictor import PREDICTOR_FACTORIES, create_predictor


def row(reliable: bool, split: str) -> LabeledWindow:
    value = .9 if reliable else .1
    return LabeledWindow(split, NodeFeatures(value, 1 - value, value, value, value, 1 - value), reliable)


class PredictorTests(unittest.TestCase):
    def test_all_predictors_share_reliability_contract(self):
        features = NodeFeatures(.8, .2, .9, .8, .7, .1)
        for name in PREDICTOR_FACTORIES:
            predictor = create_predictor(name)
            self.assertGreaterEqual(predictor.predict(features), 0.0)
            self.assertLessEqual(predictor.predict(features), 1.0)
            predictor.update(features, True)
            self.assertGreaterEqual(predictor.predict(features), 0.0)
            self.assertLessEqual(predictor.predict(features), 1.0)

    def test_validation_reports_five_metrics_and_never_accepts_test_rows(self):
        records = [*(row(index % 2 == 0, "train") for index in range(32)), *(row(index % 2 == 0, "validation") for index in range(12))]
        result = train_and_validate(records)
        self.assertEqual(set(result), set(PREDICTOR_FACTORIES))
        self.assertTrue(all(0 <= value.f1 <= 1 and 0 <= value.auroc <= 1 for value in result.values()))
        self.assertIn(select_winner(result), result)
        with self.assertRaises(ValueError): train_and_validate([*records, row(True, "test")])
