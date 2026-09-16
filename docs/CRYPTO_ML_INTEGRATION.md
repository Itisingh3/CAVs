# Cryptography and ML authority boundary

```
Credential validation -> ML-DSA authentication -> ML-KEM exchange -> key confirmation
    -> authenticated secure telemetry -> 10 CAV features -> P_ML
    -> learned reliability score -> confidence guard -> dynamic AGS-PBFT
```

The first four stages are security-authoritative. Invalid credentials,
signatures, KEM exchanges, confirmations, replayed messages, or suite
mismatches are rejected by `protocol/` before any telemetry is eligible for a
reliability decision. ML cannot repair, override, tune, or select the
cryptographic suite. Session keys, shared secrets, and private keys are never
ML features.

`credential_trust` is a protocol-derived non-secret feature. It reflects a
valid authenticated credential/session context, not an attack label and not a
guarantee that behaviour is reliable. Under low confidence, invalid features,
missing temporal history, or an unavailable model, the grouping layer falls
back to static AGS-PBFT and logs the reason.

ProVerif models the registration/AKE protocol under symbolic assumptions.
Empirical ML results assess reliability and grouping only; neither substitutes
for the other.
