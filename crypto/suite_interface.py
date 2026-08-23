from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class CryptoUnavailable(RuntimeError):
    """Raised when the maintained PQC provider is unavailable or rejects input."""


class KEMBackend(ABC):
    algorithm_id: str

    @abstractmethod
    def keygen(self) -> tuple[bytes, bytes]: ...

    @abstractmethod
    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]: ...

    @abstractmethod
    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes: ...


class SignatureBackend(ABC):
    algorithm_id: str

    @abstractmethod
    def keygen(self) -> tuple[bytes, bytes]: ...

    @abstractmethod
    def sign(self, secret_key: bytes, message: bytes) -> bytes: ...

    @abstractmethod
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool: ...


@dataclass(frozen=True)
class CryptoSuite:
    kem: KEMBackend
    signature: SignatureBackend

    @property
    def algorithm_ids(self) -> dict[str, str]:
        return {"kem_alg": self.kem.algorithm_id, "sig_alg": self.signature.algorithm_id}
