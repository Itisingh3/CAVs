import unittest

from crypto.suite_interface import CryptoSuite
from protocol.ake import AKEError, Initiator, Responder
from protocol.registration import CredentialError, issue_credential, validate_credential
from tests.fakes import TestKEM, TestSignature


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.signer, self.suite = TestSignature(), CryptoSuite(TestKEM(), TestSignature())
        self.ta_pk, self.ta_sk = self.signer.keygen()
        self.i_pk, self.i_sk = self.signer.keygen(); self.r_pk, self.r_sk = self.signer.keygen()
        self.i_credential = issue_credential(self.ta_sk, self.signer, self.i_pk, now=100, ttl_s=100).wire()
        self.r_credential = issue_credential(self.ta_sk, self.signer, self.r_pk, now=100, ttl_s=100).wire()

    def test_authenticated_key_exchange(self):
        initiator = Initiator(self.suite, self.i_credential, self.i_sk, self.ta_pk)
        responder = Responder(self.suite, self.r_credential, self.r_sk, self.ta_pk)
        state_i, hello = initiator.start(now=120); state_r, challenge = responder.accept_hello(hello, now=120)
        key_i, confirm = initiator.accept_challenge(state_i, challenge, now=120); key_r = responder.accept_confirm(state_r, confirm)
        self.assertEqual(key_i, key_r)

    def test_forged_signature_rejected(self):
        initiator = Initiator(self.suite, self.i_credential, self.i_sk, self.ta_pk); responder = Responder(self.suite, self.r_credential, self.r_sk, self.ta_pk)
        _, hello = initiator.start(now=120); hello["signature"] = "AAAA"
        with self.assertRaises(AKEError): responder.accept_hello(hello, now=120)

    def test_replay_rejected(self):
        initiator = Initiator(self.suite, self.i_credential, self.i_sk, self.ta_pk); responder = Responder(self.suite, self.r_credential, self.r_sk, self.ta_pk)
        _, hello = initiator.start(now=120); responder.accept_hello(hello, now=120)
        with self.assertRaises(AKEError): responder.accept_hello(hello, now=120)

    def test_expired_credential_rejected(self):
        with self.assertRaises(CredentialError): validate_credential(self.i_credential, self.ta_pk, self.signer, now=201)
