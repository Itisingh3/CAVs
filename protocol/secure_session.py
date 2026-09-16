"""Authenticated-session bridge for non-secret ML telemetry.

The only public output is a session identifier, pseudonym, timestamp, and
credential-status bit. Keys and KEM shared secrets remain local to the AKE and
are intentionally not represented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from protocol.ake import Initiator, Responder
from protocol.registration import validate_credential

@dataclass(frozen=True)
class AuthenticatedTelemetryContext:
    session_id: str
    pseudonym: str
    authenticated_at: int
    credential_trust: float = 1.0

def establish_authenticated_context(initiator: Initiator, responder: Responder, *, now: int) -> AuthenticatedTelemetryContext:
    """Complete credential validation, signatures, KEM and confirmation first.

    Any protocol exception prevents a context from being returned, so ML code
    cannot convert a failed cryptographic exchange into a trusted observation.
    """
    initiator_state, hello = initiator.start(now=now)
    responder_state, challenge = responder.accept_hello(hello, now=now)
    key_i, confirm = initiator.accept_challenge(initiator_state, challenge, now=now)
    key_r = responder.accept_confirm(responder_state, confirm)
    if key_i != key_r: raise RuntimeError("AKE key mismatch")
    credential = validate_credential(hello["payload"]["credential"], initiator.ta_public_key, initiator.suite.signature, now)
    return AuthenticatedTelemetryContext(initiator_state.session_id, credential.body["pid"], now)

@dataclass
class TelemetryHistory:
    """Causal local history, scoped to one authenticated session/node."""
    agreements: list[bool] = field(default_factory=list)
    faults: list[bool] = field(default_factory=list)
    participations: list[bool] = field(default_factory=list)
    reputation: float = .5

    def observe(self, *, agreed: bool, participated: bool) -> None:
        self.agreements.append(agreed); self.faults.append(not agreed); self.participations.append(participated)
        self.reputation = max(0.0, min(1.0, .9 * self.reputation + .1 * float(agreed)))
