# State machines and failure handling (v1.0.0)

## AKE initiator

`IDLE -> HELLO_SENT -> CHALLENGE_VALIDATED -> CONFIRM_SENT -> ACCEPTED`.

Failures from any nonterminal state go to `ABORTED`: invalid credential, unsupported suite, bad signature, replay, stale timestamp, session mismatch, malformed message, decapsulation exception, confirmation failure, or timeout. `ABORTED` and `ACCEPTED` erase ephemeral KEM secret material.

## AKE responder

`IDLE -> HELLO_VALIDATED -> CHALLENGE_SENT -> CONFIRM_VALIDATED -> ACCEPTED`.

The same failure set transitions to `ABORTED`. The responder records `(pid_I, sid, n_I)` in the replay cache before issuing `CHALLENGE`.

## Consensus node

`IDLE -> REQUEST_VALIDATED -> PREPREPARE_VALIDATED -> PREPARED -> RESPONDED -> COMMITTED`.

Invalid or duplicate messages are ignored and audited. A timeout triggers a view-change procedure outside this reference implementation. Score changes are based only on verified, committed outcomes.
