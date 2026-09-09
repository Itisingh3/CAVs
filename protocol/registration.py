from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from crypto.suite_interface import SignatureBackend
from protocol.codec import b64, canonical, unb64


class CredentialError(ValueError): pass


@dataclass(frozen=True)
class Credential:
    body: dict[str, Any]
    ta_signature: bytes

    def wire(self) -> dict[str, Any]:
        return {"body": self.body, "ta_signature": b64(self.ta_signature)}


def issue_credential(ta_secret_key: bytes, ta_signer: SignatureBackend, entity_public_key: bytes, ttl_s: int = 3600, now: int | None = None) -> Credential:
    now = int(time.time()) if now is None else now
    body = {"domain": "CAV-CREDENTIAL-v1", "pid": secrets.token_urlsafe(18), "sig_alg": ta_signer.algorithm_id,
            "entity_sig_pk": b64(entity_public_key), "issued_at": now, "expires_at": now + ttl_s, "credential_nonce": secrets.token_urlsafe(16)}
    return Credential(body=body, ta_signature=ta_signer.sign(ta_secret_key, canonical(body)))


def validate_credential(wire: dict[str, Any], ta_public_key: bytes, signer: SignatureBackend, now: int | None = None) -> Credential:
    now = int(time.time()) if now is None else now
    try:
        body, signature = wire["body"], unb64(wire["ta_signature"])
        required = {"domain", "pid", "sig_alg", "entity_sig_pk", "issued_at", "expires_at", "credential_nonce"}
        if set(body) != required or body["domain"] != "CAV-CREDENTIAL-v1" or body["sig_alg"] != signer.algorithm_id:
            raise CredentialError("credential format or algorithm mismatch")
        if not isinstance(body["issued_at"], int) or not isinstance(body["expires_at"], int) or not body["issued_at"] <= now <= body["expires_at"]:
            raise CredentialError("credential is not currently valid")
        if not signer.verify(ta_public_key, canonical(body), signature):
            raise CredentialError("TA signature does not verify")
        unb64(body["entity_sig_pk"])
        return Credential(body=body, ta_signature=signature)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, CredentialError): raise
        raise CredentialError("malformed credential") from exc
