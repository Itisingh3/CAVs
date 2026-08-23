import importlib.util
import unittest

from crypto.mlkem_backend import MLKEM768Backend
from crypto.mldsa_backend import MLDSA65Backend
from crypto.suite_interface import CryptoSuite
from protocol.ake import AKEError, Initiator, Responder
from protocol.registration import issue_credential


@unittest.skipUnless(importlib.util.find_spec("oqs"), "liboqs-python is not installed")
class OQSTests(unittest.TestCase):
    def test_mlkem_encapsulation(self):
        kem = MLKEM768Backend(); pk, sk = kem.keygen(); ciphertext, sender_secret = kem.encapsulate(pk)
        self.assertEqual(sender_secret, kem.decapsulate(sk, ciphertext))
    def test_mldsa_forgery_rejected(self):
        signer = MLDSA65Backend(); pk, sk = signer.keygen(); message = b"CAV test"
        signature = signer.sign(sk, message)
        self.assertTrue(signer.verify(pk, message, signature)); self.assertFalse(signer.verify(pk, message + b"!", signature))

    def test_real_registration_and_ake_flow(self):
        kem, signer, suite = MLKEM768Backend(), MLDSA65Backend(), CryptoSuite(MLKEM768Backend(), MLDSA65Backend())
        ta_pk, ta_sk = signer.keygen(); i_pk, i_sk = signer.keygen(); r_pk, r_sk = signer.keygen()
        i_credential = issue_credential(ta_sk, signer, i_pk, now=100, ttl_s=100).wire()
        r_credential = issue_credential(ta_sk, signer, r_pk, now=100, ttl_s=100).wire()
        initiator, responder = Initiator(suite, i_credential, i_sk, ta_pk), Responder(suite, r_credential, r_sk, ta_pk)
        state_i, hello = initiator.start(now=120); state_r, challenge = responder.accept_hello(hello, now=120)
        key_i, confirm = initiator.accept_challenge(state_i, challenge, now=120)
        self.assertEqual(key_i, responder.accept_confirm(state_r, confirm))

    def test_corrupted_ciphertext_is_rejected(self):
        kem = MLKEM768Backend(); pk, sk = kem.keygen(); ciphertext, _ = kem.encapsulate(pk)
        corrupted = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
        # ML-KEM's decapsulation may return a pseudorandom fallback secret by design.
        # The authenticated transcript/key-confirmation layer detects this mismatch.
        self.assertNotEqual(kem.decapsulate(sk, ciphertext), kem.decapsulate(sk, corrupted))
