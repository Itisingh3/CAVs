# Formal-verification scope and reproduction

Run the final composed model with:

```powershell
& 'C:\Tools\proverif2.05\proverif.exe' formal\composed_protocol.pv | Tee-Object results\formal\composed_protocol_results.txt
```

The model covers a TA-signed credential, signed suite identifiers in the AKE, an ephemeral-KEM shared-secret abstraction, verified key confirmation and transcript binding, and signed PBFT-vote origin. Its completed queries establish injective initiator/responder authentication, authenticated suite acceptance at the responder, and vote-origin correspondence.

It is a symbolic Dolev--Yao model. It does not establish implementation security, ML-KEM/ML-DSA computational security, availability, side-channel resistance, timestamp/replay-cache implementation correctness, or end-to-end network properties. The separately retained `secrecy_equivalence.pv` remains an isolated KEM/KDF equivalence check; it must not be cited as a complete credential/replay-cache forward-secrecy proof until that composed equivalence model and its output are archived.
