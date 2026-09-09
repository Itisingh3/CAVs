"""ML-KEM-768 adapter for liboqs-python. It fails closed if OQS is absent."""
from __future__ import annotations

from crypto.suite_interface import CryptoUnavailable, KEMBackend


class MLKEM768Backend(KEMBackend):
    algorithm_id = "ML-KEM-768"

    @staticmethod
    def _oqs():
        try:
            import oqs  # type: ignore
            return oqs
        except ImportError as exc:
            raise CryptoUnavailable("liboqs-python is required for ML-KEM-768; install the documented maintained provider") from exc

    def keygen(self) -> tuple[bytes, bytes]:
        oqs = self._oqs()
        try:
            with oqs.KeyEncapsulation(self.algorithm_id) as kem:
                public_key = kem.generate_keypair()
                return public_key, kem.export_secret_key()
        except Exception as exc:
            raise CryptoUnavailable(f"ML-KEM key generation failed: {exc}") from exc

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        oqs = self._oqs()
        try:
            with oqs.KeyEncapsulation(self.algorithm_id) as kem:
                ciphertext, shared_secret = kem.encap_secret(public_key)
                return ciphertext, shared_secret
        except Exception as exc:
            raise CryptoUnavailable("ML-KEM encapsulation rejected the public key") from exc

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        oqs = self._oqs()
        try:
            with oqs.KeyEncapsulation(self.algorithm_id, secret_key) as kem:
                return kem.decap_secret(ciphertext)
        except Exception as exc:
            raise CryptoUnavailable("ML-KEM decapsulation failed; ciphertext is rejected") from exc
