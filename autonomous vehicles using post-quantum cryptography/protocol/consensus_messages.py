from __future__ import annotations

import time
from typing import Any

from crypto.suite_interface import SignatureBackend
from protocol.codec import b64, canonical, unb64


def build_signed_message(message_type: str, sender_pid: str, view: int, sequence: int, digest: str, signer: SignatureBackend, secret_key: bytes, now: int | None = None) -> dict[str, Any]:
    payload = {"domain":"CAV-CONSENSUS-v1","type":message_type,"sender_pid":sender_pid,"view":view,"sequence":sequence,"digest":digest,"ts":int(time.time()) if now is None else now,"sig_alg":signer.algorithm_id}
    return {"payload":payload,"signature":b64(signer.sign(secret_key, canonical(payload)))}


def verify_signed_message(wire: dict[str, Any], public_key: bytes, signer: SignatureBackend, freshness_s: int = 30, now: int | None = None) -> bool:
    try:
        p = wire["payload"]
        return p["domain"] == "CAV-CONSENSUS-v1" and p["sig_alg"] == signer.algorithm_id and abs((int(time.time()) if now is None else now) - p["ts"]) <= freshness_s and signer.verify(public_key, canonical(p), unb64(wire["signature"]))
    except (KeyError, TypeError, ValueError): return False
