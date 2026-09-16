import unittest

from consensus.ags_pbft_baseline import AGSConfig
from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from ml.secure_grouping_pipeline import NetworkTelemetry, SecureTemporalGroupingPipeline
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence
from protocol.secure_session import AuthenticatedTelemetryContext

class ConstantSequenceModel:
    def predict_sequences(self, sequences): return [.9] * len(sequences)

class SecureGroupingPipelineTests(unittest.TestCase):
    def test_authenticated_causal_sequence_reaches_scored_grouping(self):
        ids = [f"n{i}" for i in range(7)]
        good, bad = TemporalEvidence(.9,.1,.9,.9,.8,.1,.8,.8,.8,1), TemporalEvidence(.1,.9,.1,.1,.1,.9,.1,.1,.1,.5)
        score = LearnedReliabilityScore(epochs=10).fit([(good,.9,True),(bad,.1,False)] * 5)
        engine = MLAdaptiveAGSPBFT(ids, 2, AGSConfig(reassignment_window=1), reliability_score=score)
        pipeline = SecureTemporalGroupingPipeline(engine, ConstantSequenceModel(), sequence_length=2)
        contexts = {node: AuthenticatedTelemetryContext(f"s-{node}", f"p-{node}", 1) for node in ids}
        for node in ids: pipeline.register_session(node, contexts[node])
        network = {node: NetworkTelemetry(.1,.9,.9,.8) for node in ids}
        pipeline.group("1", contexts, network, load=.2)
        self.assertTrue(any(event.get("reason") == "sequence_unavailable" for event in engine.events))
        for round_id in range(2, 11):
            pipeline.record_consensus_outcome(set(ids))
            pipeline.group(str(round_id), contexts, network, load=.2)
        self.assertTrue(any(event["event"] == "ml_reassignment" for event in engine.events))

    def test_unregistered_context_cannot_reach_model(self):
        ids = [f"n{i}" for i in range(7)]; engine = MLAdaptiveAGSPBFT(ids, 2)
        pipeline = SecureTemporalGroupingPipeline(engine, ConstantSequenceModel(), sequence_length=1)
        contexts = {node: AuthenticatedTelemetryContext(f"s-{node}", f"p-{node}", 1) for node in ids}
        pipeline.group("1", contexts, {node: NetworkTelemetry(.1,.9,.9,.8) for node in ids}, load=.2)
        self.assertTrue(any(event["event"] == "ml_fallback" for event in engine.events))
