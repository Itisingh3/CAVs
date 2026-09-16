# Formal-verification scope and reproduction

Run the frozen final AKE model and generate machine-readable evidence with:

```powershell
python -m analysis.verify_formal --proverif 'C:\Tools\proverif2.05\proverif.exe' --output reports\formal
```

`formal/model.pv` is the authoritative final symbolic AKE: TA-issued
credentials, signed HELLO/CHALLENGE/CONFIRM, suite binding, fresh timestamp
tokens, ML-KEM shared-secret abstraction, transcript-bound confirmation, and
a serialised replay-cache abstraction. Its queries establish injective
initiator/responder authentication, suite agreement, and that a replay-cache
claim originates from a signed HELLO. The `replayed` table is guarded by a
private token, representing the atomic lookup/insert required of the runtime
replay cache.

It is a symbolic Dolev--Yao model. It does not establish implementation
security, ML-KEM/ML-DSA computational security, availability, side-channel
resistance, wall-clock timeout correctness, or end-to-end network properties.
The separately retained `secrecy_equivalence.pv` remains an isolated KEM/KDF
equivalence check; it is not a complete credential/replay-cache AKE secrecy or
forward-secrecy proof. ML is intentionally outside the ProVerif scope.
