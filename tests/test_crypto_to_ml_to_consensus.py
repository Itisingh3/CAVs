import unittest

from consensus.ags_pbft_ml import MLAdaptiveAGSPBFT
from consensus.ags_pbft_baseline import AGSConfig
from crypto.suite_interface import CryptoSuite
from ml.temporal_reliability import LearnedReliabilityScore, TemporalEvidence
from protocol.ake import AKEError, Initiator, Responder
from protocol.registration import issue_credential
from protocol.secure_session import establish_authenticated_context
from tests.fakes import TestKEM, TestSignature

class CryptoMLConsensusIntegrationTests(unittest.TestCase):
    def setUp(self):
        signer = TestSignature(); self.suite = CryptoSuite(TestKEM(), signer); self.ta_pk, self.ta_sk = signer.keygen(); self.i_pk, self.i_sk = signer.keygen(); self.r_pk, self.r_sk = signer.keygen()
        self.i_credential = issue_credential(self.ta_sk, signer, self.i_pk, now=100, ttl_s=100).wire(); self.r_credential = issue_credential(self.ta_sk, signer, self.r_pk, now=100, ttl_s=100).wire()

    def test_authenticated_context_contains_no_secret_and_can_drive_scored_grouping(self):
        context = establish_authenticated_context(Initiator(self.suite, self.i_credential, self.i_sk, self.ta_pk), Responder(self.suite, self.r_credential, self.r_sk, self.ta_pk), now=120)
        self.assertEqual(context.credential_trust, 1.0); self.assertFalse(hasattr(context, "session_key"))
        ids, evidence = [f"n{i}" for i in range(7)], TemporalEvidence(.9, .1, .9, .9, .8, .1, .8, .8, .8, context.credential_trust)
        scorer = LearnedReliabilityScore(epochs=10).fit([(evidence, .9, True), (TemporalEvidence(.1,.9,.1,.1,.1,.9,.1,.1,.1,.5), .1, False)] * 5)
        engine = MLAdaptiveAGSPBFT(ids, 2, AGSConfig(reassignment_window=1), reliability_score=scorer)
        engine.reassign_with_temporal_probabilities("1", {node: evidence for node in ids}, {node: .9 for node in ids}, .2, observations=12)
        self.assertTrue(any(event["event"] == "ml_reassignment" for event in engine.events))

    def test_invalid_signature_cannot_create_ml_context(self):
        initiator, responder = Initiator(self.suite, self.i_credential, self.i_sk, self.ta_pk), Responder(self.suite, self.r_credential, self.r_sk, self.ta_pk)
        _, hello = initiator.start(now=120); hello["signature"] = "AAAA"
        with self.assertRaises(AKEError): responder.accept_hello(hello, now=120)
