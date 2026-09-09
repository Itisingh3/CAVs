"""ML-DSA-65 adapter for liboqs-python."""
from __future__ import annotations

from crypto.suite_interface import CryptoUnavailable, SignatureBackend


class MLDSA65Backend(SignatureBackend):
    algorithm_id = "ML-DSA-65"

    @staticmethod
    def _oqs():
        try:
            import oqs  # type: ignore
            return oqs
        except ImportError as exc:
            raise CryptoUnavailable("liboqs-python is required for ML-DSA-65; install the documented maintained provider") from exc

    def keygen(self) -> tuple[bytes, bytes]:
        oqs = self._oqs()
        try:
            with oqs.Signature(self.algorithm_id) as signer:
                public_key = signer.generate_keypair()
                return public_key, signer.export_secret_key()
        except Exception as exc:
            raise CryptoUnavailable(f"ML-DSA key generation failed: {exc}") from exc

    def sign(self, secret_key: bytes, message: bytes) -> bytes:
        oqs = self._oqs()
        try:
            with oqs.Signature(self.algorithm_id, secret_key) as signer:
                return signer.sign(message)
        except Exception as exc:
            raise CryptoUnavailable("ML-DSA signing failed") from exc

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        oqs = self._oqs()
        try:
            with oqs.Signature(self.algorithm_id) as signer:
                return bool(signer.verify(message, signature, public_key))
        except Exception:
            return False
