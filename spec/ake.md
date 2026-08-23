# Authenticated KEM key establishment (v1.0.0)

The initiator `I` and responder `R` have TA-issued ML-DSA credentials. `I` generates a fresh ML-KEM-768 ephemeral key pair `(pk_I, sk_I)` for every attempted session.

1. `I -> R`: `HELLO = {domain, type, sid, n_I, ts, kem_alg, sig_alg, pk_I, cred_I}` and `σ_I = SIG.Sign(sk_sig_I, HELLO)`.
2. `R` validates `cred_I`, freshness of `ts`, uniqueness of `(pid_I, sid, n_I)`, and `σ_I`. It generates `n_R` and computes `(ct, ss) = KEM.Encap(pk_I)`.
3. `R -> I`: `CHALLENGE = {domain, type, sid, n_I, n_R, ts, kem_alg, sig_alg, ct, cred_R}` and `σ_R = SIG.Sign(sk_sig_R, CHALLENGE)`.
4. `I` validates `cred_R`, nonces, freshness, and `σ_R`; it derives `ss = KEM.Decap(sk_I, ct)`, `th = H(HELLO || σ_I || CHALLENGE || σ_R)`, and `K_s = H("CAV-AKE-v1" || ss || th)`.
5. `I -> R`: `CONFIRM = {domain, type, sid, th, tag = HMAC(K_s, "initiator-confirm" || th)}` and `σ_I' = SIG.Sign(sk_sig_I, CONFIRM)`.
6. `R` verifies `σ_I'`, calculates the same `th` and `K_s`, and checks the confirmation tag. Only then does it accept the session.

Nonces and the replay cache are mandatory. A session times out if any step is not completed within the configured freshness window. Any signature, credential, nonce, timestamp, transcript, ciphertext-decapsulation, or confirmation failure aborts the session and is logged as a typed failure; no key is exposed to the caller.

Security rationale: identity authentication is provided by ML-DSA credentials and signatures; key secrecy is reduced to ML-KEM confidentiality and KDF assumptions. The ephemeral KEM secret is erased after acceptance. Forward secrecy is conditional on secure erasure and does not cover compromise of the signing credential during an active session.
