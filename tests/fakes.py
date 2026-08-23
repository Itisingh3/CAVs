"""Test-only deterministic double. It is never a cryptographic backend or experiment option."""
import hashlib
import hmac
import secrets
from crypto.suite_interface import KEMBackend, SignatureBackend


class TestKEM(KEMBackend):
    algorithm_id = "TEST-KEM-NOT-PQC"
    def keygen(self):
        secret = secrets.token_bytes(32); return secret, secret
    def encapsulate(self, public_key):
        secret = secrets.token_bytes(32); return bytes(a ^ b for a, b in zip(secret, public_key)), secret
    def decapsulate(self, secret_key, ciphertext): return bytes(a ^ b for a, b in zip(secret_key, ciphertext))


class TestSignature(SignatureBackend):
    algorithm_id = "TEST-SIG-NOT-PQC"
    def keygen(self):
        secret = secrets.token_bytes(32); return secret, secret
    def sign(self, secret_key, message): return hmac.new(secret_key, message, hashlib.sha3_256).digest()
    def verify(self, public_key, message, signature): return hmac.compare_digest(self.sign(public_key, message), signature)
