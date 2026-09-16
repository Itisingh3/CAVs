# Notation and protocol binding (v1.0.0)

| Symbol | Meaning |
| --- | --- |
| `TA` | Trusted authority and credential issuer |
| `E` | CAV, RSU, MEC server, or consensus participant |
| `pid` | TA-issued pseudonymous identifier; never the long-term real identifier |
| `KEM` | ML-KEM-768, identified as `ML-KEM-768` |
| `SIG` | ML-DSA-65, identified as `ML-DSA-65` |
| `(pk_e, sk_e)` | Ephemeral ML-KEM key pair for one AKE session |
| `(pk_sig, sk_sig)` | Entity ML-DSA credential key pair |
| `cred` | TA-signed canonical credential bundle |
| `sid` | 256-bit session identifier |
| `n_I`, `n_R` | Initiator and responder nonces |
| `ct, ss` | KEM ciphertext and shared secret |
| `th` | SHA3-256 hash of the canonical AKE transcript |
| `K_s` | `SHA3-256("CAV-AKE-v1" || ss || th)` session key |
| `σ_X(m)` | ML-DSA signature by entity `X` over canonical bytes of `m` |

All structured messages are canonical JSON encoded as UTF-8 with sorted keys and compact separators. Byte fields are Base64-encoded. Every signed object contains a literal `domain` field; signatures are invalid outside that protocol context.

The specification excludes anonymity against a global active observer, side-channel resistance, denial-of-service prevention, and blockchain safety outside the usual PBFT bound `n >= 3f+1`.
