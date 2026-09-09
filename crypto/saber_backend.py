"""Experimental Saber placeholder. Do not use for paper claims without PQClean/liboqs integration."""
from crypto.suite_interface import CryptoUnavailable, KEMBackend


class ExperimentalSaberBackend(KEMBackend):
    algorithm_id = "SABER-EXPERIMENTAL"

    def _disabled(self):
        raise CryptoUnavailable("Saber is experimental and intentionally disabled until a maintained PQClean/liboqs binding is configured")

    def keygen(self): return self._disabled()
    def encapsulate(self, public_key: bytes): return self._disabled()
    def decapsulate(self, secret_key: bytes, ciphertext: bytes): return self._disabled()
