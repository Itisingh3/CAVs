# Registration (v1.0.0)

1. The TA owns a long-term ML-DSA-65 signing key. Its public key is distributed through an authenticated out-of-band trust anchor.
2. An entity generates a long-term ML-DSA-65 credential key pair locally. Private keys are never sent to the TA.
3. The TA issues a credential containing `pid`, the entity signing public key, `issued_at`, `expires_at`, a credential nonce, and the fixed signature algorithm identifier `ML-DSA-65`.
4. The TA signs the canonical credential body with domain `CAV-CREDENTIAL-v1`. The pair `{body, ta_signature}` is the credential.
5. A receiver accepts a credential only if the algorithm identifiers match the locally supported suite, the TA signature verifies, and `issued_at <= now <= expires_at`.

The credential contains no KEM public key. Each AKE generates a fresh ML-KEM ephemeral public key, which is authenticated by the holder of the credential signing key. This avoids incorrectly claiming forward secrecy from a static KEM key.

Abort rule: malformed Base64, unsupported algorithms, invalid TA signature, or expired credential terminates the exchange without emitting a response.
