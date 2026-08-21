from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from crypto.suite_interface import CryptoSuite
from protocol.codec import b64, canonical, sha3, unb64
from protocol.registration import CredentialError, validate_credential


class AKEError(ValueError): pass


def _timestamp(now: int | None) -> int: return int(time.time()) if now is None else now
def _check_fresh(ts: int, now: int, freshness_s: int):
    if not isinstance(ts, int) or abs(now - ts) > freshness_s: raise AKEError("stale message")
def _sig_message(payload: dict[str, Any]) -> bytes: return canonical(payload)
def _transcript(hello: dict[str, Any], challenge: dict[str, Any]) -> bytes: return sha3(canonical(hello) + canonical(challenge))
def _session_key(shared_secret: bytes, th: bytes) -> bytes: return sha3(b"CAV-AKE-v1" + shared_secret + th)


@dataclass
class ReplayCache:
    seen: set[tuple[str, str, str]] = field(default_factory=set)
    def claim(self, pid: str, sid: str, nonce: str) -> None:
        item = (pid, sid, nonce)
        if item in self.seen: raise AKEError("replayed HELLO")
        self.seen.add(item)


@dataclass
class InitiatorState:
    session_id: str
    nonce_i: str
    ephemeral_secret_key: bytes
    hello: dict[str, Any]
    hello_signature: bytes


class Initiator:
    def __init__(self, suite: CryptoSuite, credential: dict[str, Any], signing_secret_key: bytes, ta_public_key: bytes, freshness_s: int = 30):
        self.suite, self.credential, self.signing_secret_key, self.ta_public_key, self.freshness_s = suite, credential, signing_secret_key, ta_public_key, freshness_s

    def start(self, now: int | None = None) -> tuple[InitiatorState, dict[str, Any]]:
        now = _timestamp(now)
        validate_credential(self.credential, self.ta_public_key, self.suite.signature, now)
        ephemeral_pk, ephemeral_sk = self.suite.kem.keygen()
        sid, nonce_i = secrets.token_urlsafe(24), secrets.token_urlsafe(18)
        hello = {"domain":"CAV-AKE-v1","type":"HELLO","sid":sid,"nonce_i":nonce_i,"ts":now,"pk_i":b64(ephemeral_pk),"credential":self.credential, **self.suite.algorithm_ids}
        signature = self.suite.signature.sign(self.signing_secret_key, _sig_message(hello))
        return InitiatorState(sid, nonce_i, ephemeral_sk, hello, signature), {"payload":hello,"signature":b64(signature)}

    def accept_challenge(self, state: InitiatorState, wire: dict[str, Any], now: int | None = None) -> tuple[bytes, dict[str, Any]]:
        now = _timestamp(now)
        try:
            challenge, signature = wire["payload"], unb64(wire["signature"])
            if challenge.get("domain") != "CAV-AKE-v1" or challenge.get("type") != "CHALLENGE": raise AKEError("wrong challenge domain/type")
            if challenge.get("sid") != state.session_id or challenge.get("nonce_i") != state.nonce_i: raise AKEError("session mismatch")
            if challenge.get("kem_alg") != self.suite.kem.algorithm_id or challenge.get("sig_alg") != self.suite.signature.algorithm_id: raise AKEError("suite mismatch")
            _check_fresh(challenge["ts"], now, self.freshness_s)
            cred = validate_credential(challenge["credential"], self.ta_public_key, self.suite.signature, now)
            if not self.suite.signature.verify(unb64(cred.body["entity_sig_pk"]), _sig_message(challenge), signature): raise AKEError("invalid responder signature")
            secret = self.suite.kem.decapsulate(state.ephemeral_secret_key, unb64(challenge["ciphertext"]))
            th, key = _transcript(state.hello, challenge), _session_key(secret, _transcript(state.hello, challenge))
            confirm = {"domain":"CAV-AKE-v1","type":"CONFIRM","sid":state.session_id,"th":b64(th),"tag":b64(hmac.new(key, b"initiator-confirm" + th, hashlib.sha3_256).digest())}
            return key, {"payload":confirm,"signature":b64(self.suite.signature.sign(self.signing_secret_key, _sig_message(confirm)))}
        finally:
            state.ephemeral_secret_key = b""  # secure erasure is environment-dependent; avoid retaining reference


@dataclass
class ResponderState:
    hello: dict[str, Any]
    hello_signature: bytes
    challenge: dict[str, Any]
    shared_secret: bytes
    initiator_public_key: bytes


class Responder:
    def __init__(self, suite: CryptoSuite, credential: dict[str, Any], signing_secret_key: bytes, ta_public_key: bytes, freshness_s: int = 30):
        self.suite, self.credential, self.signing_secret_key, self.ta_public_key, self.freshness_s = suite, credential, signing_secret_key, ta_public_key, freshness_s
        self.replay_cache = ReplayCache()

    def accept_hello(self, wire: dict[str, Any], now: int | None = None) -> tuple[ResponderState, dict[str, Any]]:
        now = _timestamp(now)
        try:
            hello, signature = wire["payload"], unb64(wire["signature"])
            if hello.get("domain") != "CAV-AKE-v1" or hello.get("type") != "HELLO": raise AKEError("wrong hello domain/type")
            if hello.get("kem_alg") != self.suite.kem.algorithm_id or hello.get("sig_alg") != self.suite.signature.algorithm_id: raise AKEError("suite mismatch")
            _check_fresh(hello["ts"], now, self.freshness_s)
            cred = validate_credential(hello["credential"], self.ta_public_key, self.suite.signature, now)
            if not self.suite.signature.verify(unb64(cred.body["entity_sig_pk"]), _sig_message(hello), signature): raise AKEError("invalid initiator signature")
            self.replay_cache.claim(cred.body["pid"], hello["sid"], hello["nonce_i"])
            ciphertext, shared_secret = self.suite.kem.encapsulate(unb64(hello["pk_i"]))
            challenge = {"domain":"CAV-AKE-v1","type":"CHALLENGE","sid":hello["sid"],"nonce_i":hello["nonce_i"],"nonce_r":secrets.token_urlsafe(18),"ts":now,"ciphertext":b64(ciphertext),"credential":self.credential,**self.suite.algorithm_ids}
            challenge_sig = self.suite.signature.sign(self.signing_secret_key, _sig_message(challenge))
            return ResponderState(hello, signature, challenge, shared_secret, unb64(cred.body["entity_sig_pk"])), {"payload":challenge,"signature":b64(challenge_sig)}
        except (CredentialError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, AKEError): raise
            raise AKEError("malformed HELLO") from exc

    def accept_confirm(self, state: ResponderState, wire: dict[str, Any]) -> bytes:
        try:
            confirm, signature = wire["payload"], unb64(wire["signature"])
            if confirm.get("domain") != "CAV-AKE-v1" or confirm.get("type") != "CONFIRM" or confirm.get("sid") != state.hello["sid"]: raise AKEError("invalid confirmation")
            if not self.suite.signature.verify(state.initiator_public_key, _sig_message(confirm), signature): raise AKEError("invalid confirmation signature")
            th, key = _transcript(state.hello, state.challenge), _session_key(state.shared_secret, _transcript(state.hello, state.challenge))
            if not hmac.compare_digest(unb64(confirm["th"]), th) or not hmac.compare_digest(unb64(confirm["tag"]), hmac.new(key, b"initiator-confirm" + th, hashlib.sha3_256).digest()): raise AKEError("key confirmation failed")
            return key
        finally:
            state.shared_secret = b""
