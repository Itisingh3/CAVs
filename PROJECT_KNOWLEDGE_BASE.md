# Project Knowledge Base: Crypto-Agile, ML-Predictive AGS-PBFT for CAVs

**Purpose.** This file consolidates the concepts, results, implementation knowledge, and paper plan learned to date. It is deliberately evidence-labelled:

- **Base-paper reported**: a claim or result made by the 2025 source paper; it is not independently reproduced here.
- **Our verified implementation result**: measured or checked in this repository.
- **Planned paper result**: required experiment/proof work that has not yet been completed; it must not be stated as a result in the letter.

The frozen protocol version is **1.0.0**. The source paper is `1-s2.0-S2214209625000075-main (1).pdf`; its extracted design is the motivation and comparison baseline, not code to copy uncritically.

---

## 1. Problem and system knowledge

### 1.1 CAV/V2X setting

- Connected and autonomous vehicles communicate through V2V, V2I/V2R, V2N, roadside units (RSUs), mobile-edge-computing (MEC) servers, and cloud services.
- Safety-critical vehicular messages need low latency, high packet-delivery ratio (PDR), authenticity, integrity, confidentiality, and resilience to mobile/dynamic topology.
- CAV communication is exposed to eavesdropping, tampering, replay, impersonation, man-in-the-middle (MITM), denial of service, malicious/Byzantine nodes, and central-server single points of failure.
- Blockchain is useful only where distributed auditability and agreement are needed. It is not appropriate to put every real-time safety message through a heavyweight consensus path.
- PBFT provides safety under the standard fault bound `n >= 3f + 1`, requiring at least `2f + 1` matching valid responses to commit.

### 1.2 Quantum and post-quantum security knowledge

- Classical RSA, DH/ECDH, and ECDSA do not provide long-term protection against a cryptographically relevant quantum computer.
- **ML-KEM** (the standardized name for CRYSTALS-Kyber) is a key-encapsulation mechanism. It establishes a shared secret; it is **not** a signature scheme.
- **ML-DSA** (the standardized name for CRYSTALS-Dilithium) provides digital signatures. It is the correct primitive for authenticating the TA, AKE messages, and PBFT messages.
- ML-KEM-768 and ML-DSA-65 are the default choices because they are standardized by NIST FIPS 203 and FIPS 204, respectively.
- Crypto-agility means a protocol can replace or adapt algorithms while preserving security and operation. It requires explicit algorithm identifiers, modular interfaces, and a migration mechanism; merely benchmarking two algorithms is not crypto-agility.
- Saber remains an **experimental** alternate KEM backend only. It must be labelled experimental in code, tables, and prose; it is not a co-default with ML-KEM.
- No cryptographic primitive is hand implemented. The implementation uses the maintained Open Quantum Safe `liboqs-python` interface.

### 1.3 ML and evaluation knowledge

- The proposed ML component is deliberately small: online logistic regression, not deep learning. This is a deployment decision for OBU-class resource constraints, not a claim of a new ML architecture.
- Per-node inputs are agreement rate, normalized RTT, PDR, link quality/mobility signal, score trend, and recent-fault rate.
- The model predicts next-window node reliability. Aggregate congestion is derived from PDR/RTT; these outputs select consensus membership and group size.
- A fallback guard is mandatory. Low confidence, invalid features, or fewer than 10 labels immediately returns to the best static policy and logs the reason.
- Training, validation, and test simulation seeds must be separated before tuning. Final statistics must use untouched test seeds.

---

## 2. What the base paper contributes and reports

### 2.1 Base architecture and mechanism

The base paper proposes a four-layer CAV architecture:

1. **User layer:** CAVs with onboard units and V2V/V2I communication.
2. **MEC layer:** RSUs and edge servers for low-latency processing.
3. **Consensus layer:** a blockchain ledger maintained by AGS-PBFT.
4. **Cloud layer:** non-time-critical storage and analytics.

Its intended approach combines Kyber/KEM-style PQC with Adaptive Grouping Score-based PBFT (AGS-PBFT). It defines an initial node score of 100 and divides nodes into consensus and candidate sets. Nodes agreeing with a committed result receive `+1`; disagreeing nodes receive `-5`. At every 50 requests, the source paper uses score mean `mu` and standard deviation `sigma` to classify/reassign nodes around `mu - sigma` and `mu + sigma`, and states that group size should change with network activity.

### 2.2 Base-paper reported simulation configuration

The source paper reports:

- OMNeT++ 6.0, SUMO 1.20.0, Veins 5.2, and PQClean.
- Hyperledger Fabric 2.2, IEEE 802.11p, a 5 km x 5 km urban grid, 600 s simulation time, and 6 Mbps data rate.
- Vehicle density from 50 to 300, nominal speed 10 m/s, and 10–15 consensus nodes.
- Kyber parameters `n=256`, `k=4`, `q=3329`, and public/secret/ciphertext sizes reported as 1568/3168/1568 bytes.

### 2.3 Base-paper reported outcomes (not reproduced)

- Reported computation cost: approximately **10.31 ms** for the proposed Kyber-AGS-PBFT scheme, compared with 14.64–359.86 ms for selected prior schemes.
- Reported end-to-end latency: approximately **920.70 ms** at 50 vehicles, **1751.20 ms** at 150 vehicles, and **2300 ms** at 300 vehicles.
- Reported throughput improvements relative to four selected schemes: **59.30%**, **71.32%**, **76.47%**, and **78.68%**.
- The paper claims lower latency, higher throughput, lower computation cost, and stronger security than its selected comparison schemes.

These numbers are source-paper claims. They must not be reused as results for this letter. Our paper must generate its own traceable data with a fixed protocol, multi-seed runs, confidence intervals, and matched baselines.

### 2.4 Base-paper limitations and gaps identified

1. **Undefined signatures:** the paper uses `Sign_c`, `Sign_l`, and `Sign_r`, but does not define a signature scheme, keys, verification algorithm, or secure construction. Referring to “Kyber signatures” is technically incorrect because Kyber/ML-KEM is a KEM.
2. **Registration-token issue:** its hash token includes a TA master key and is not an independently verifiable digital signature. It is not a sufficient public credential-binding mechanism.
3. **AKE underspecification:** message formats, key confirmation, replay cache behavior, authenticated key binding, session identifiers, abort paths, and ephemeral-key erasure are incomplete.
4. **Forward-secrecy overclaim risk:** static KEM material alone does not establish forward secrecy. An ephemeral KEM key must be used per session and erased.
5. **Static AGS-PBFT policy:** `+1/-5`, `mu±sigma`, the 50-request window, and “low/high activity” group sizing lack a predictive definition or empirical justification.
6. **No formal model/proof:** prose security discussion is not a game-based proof or formal verification of the composed registration-plus-AKE protocol.
7. **Insufficient statistical rigor:** the source reports point comparisons but does not establish a multi-seed confidence-interval and paired-significance workflow.
8. **Crypto agility absent:** the construction is hard-coded to Kyber terminology and lacks negotiated suite identifiers/abstraction boundaries.

---

## 3. Our frozen design and implementation knowledge

### 3.1 Protocol specification

The protocol source of truth is the `spec/` directory.

- **Credential:** TA signs a canonical, pseudonymous credential containing an entity ML-DSA public key, issue/expiry times, nonce, and algorithm identifier.
- **Privacy scope:** the design uses a pseudonymous identifier, but does not claim anonymity against a global active observer.
- **Initiator AKE:** generates a fresh ML-KEM-768 ephemeral key pair for every session; signs the `HELLO` with ML-DSA-65.
- **Responder AKE:** validates the TA credential, freshness, replay cache, and initiator signature; encapsulates a secret to the initiator ephemeral KEM key; signs `CHALLENGE` with ML-DSA-65.
- **Key confirmation:** initiator decapsulates, hashes the transcript, derives the session key, and returns a signed HMAC-based confirmation. The responder accepts only after verifying it.
- **Replay protection:** session identifier, initiator/responder nonces, timestamps, and a `(pseudonym, session ID, nonce)` replay cache are checked.
- **Abort behavior:** unsupported suite, malformed object, bad credential, expired credential, bad signature, stale message, session mismatch, decapsulation failure, confirmation failure, and timeout abort without releasing a session key.
- **Consensus:** `REQUEST`, `PRE-PREPARE`, `PREPARE`, `RESPONSE`, and `REPLY` carry a `CAV-CONSENSUS-v1` domain, sender pseudonym, view, sequence, digest, timestamp, suite identifier, and ML-DSA signature.

### 3.2 Crypto-agility boundary

- `crypto/suite_interface.py` defines KEM and signature interfaces.
- `crypto/mlkem_backend.py` wraps maintained ML-KEM-768; `crypto/mldsa_backend.py` wraps ML-DSA-65.
- Every AKE/consensus message includes KEM and signature algorithm identifiers.
- `crypto/saber_backend.py` exists only as a fail-closed experimental placeholder; it performs no hand-rolled or unlabelled Saber operation.

### 3.3 AGS-PBFT baseline and ML extension

- `consensus/ags_pbft_baseline.py` defaults exactly to the base paper: initial 100, `+1/-5`, threshold multiplier 1.0 (`mu±sigma`), and 50 requests.
- All static parameters are configurable for the ablation sweep.
- It logs score updates, network events, reassignments, group transitions, thresholds, and consensus-set size.
- `consensus/ags_pbft_ml.py` preserves score updates but defers membership reassignment to the ML policy. This avoids silently executing static reassignment before ML reassignment.
- Low-confidence ML explicitly invokes the static policy and records `ml_fallback`.

### 3.4 Reproducibility implementation

- The deterministic development harness writes a manifest and structured JSONL events for every run.
- The manifest records variant, seed, density, rounds, Python/platform metadata, and an explicit warning that it is not a Veins result.
- `sim/seed_manager.py` performs train/validation/test splitting.
- `analysis/stats.py` calculates mean and 95% CI from logged metrics.
- `analysis/ablation_sweep.py` generates the static configuration grid.
- The final simulator must use the defined JSONL event schema when connected to SUMO/Veins/OMNeT++.

---

## 4. Verified implementation results

### 4.1 Hardware and execution environment

- CPU used: AMD Ryzen 5 5600H at 3.30 GHz.
- RAM: 8 GB (7.34 GB usable).
- GPU: NVIDIA GeForce GTX 1650 4 GB is **not used**.
- External hardware devices: **none**.
- The design is CPU-first and GPU-independent; no deep-learning framework is used.

### 4.2 PQC microbenchmark on this machine

Results from `results/benchmarks/pqc_actual_machine.csv`, 20 repetitions, maintained `liboqs-python` provider:

| Algorithm | Operation | Mean time (ms) | Measured size |
| --- | --- | ---: | --- |
| ML-KEM-768 | Key generation | 10.763775 | public key 1184 B; secret key 2400 B |
| ML-KEM-768 | Encapsulation | 0.612490 | ciphertext 1088 B |
| ML-KEM-768 | Decapsulation | 0.682750 | shared secret 32 B |
| ML-DSA-65 | Key generation | 1.217680 | public key 1952 B; secret key 4032 B |
| ML-DSA-65 | Signing | 5.859975 | signature 3309 B |
| ML-DSA-65 | Verification | 1.660305 | — |

These are valid local microbenchmarks, not vehicular-network or hardware-OBU results. They support an honest overhead discussion: ML-DSA adds substantial message size and signing cost relative to an undefined/hash token, in exchange for actual signature authentication.

### 4.3 Test results

All **10** current tests passed with the real ML-KEM/ML-DSA provider:

- Valid ML-KEM encapsulation/decapsulation.
- ML-DSA valid-signature verification and forged-message rejection.
- Real TA registration plus end-to-end signed AKE/key confirmation.
- Corrupted ML-KEM ciphertext produces a different decapsulation result; the authenticated confirmation layer detects a key mismatch.
- Expired credentials are rejected.
- Forged signatures and replayed HELLO messages are rejected.
- Base-paper default score deltas/reassignment behavior is exercised.
- ML grouping falls back to static policy before adequate labelled observations exist.

### 4.4 Formal-model results

The ProVerif core model returned:

- `AcceptedI(sid,key) ==> Responded(sid)` is true.
- `AcceptedR(sid,key) ==> Initiated(sid)` is true.
- The isolated ephemeral-KEM/KDF observational-equivalence secrecy model is true.

Interpretation boundary: these are symbolic-model checks of the stated abstraction. They do **not** prove implementation security, timing/side-channel resistance, availability, ML correctness, or the complete deployment credential/replay-store implementation. The complete model must be updated and rerun whenever the frozen protocol changes.

### 4.5 Development-simulator smoke result (not a research claim)

A deterministic 12-round development run at density 12 produced the following values for both variants:

| Variant | Mean latency (ms) | 95% CI (ms) | Mean PDR | Mean throughput (packets/round) | Mean consensus size |
| --- | ---: | ---: | ---: | ---: | ---: |
| Static baseline | 60.1417 | 1.2158 | 0.8329 | 11.1667 | 6.0 |
| ML adaptive | 60.1417 | 1.2158 | 0.8329 | 11.1667 | 6.0 |

These are only smoke-test values from a lightweight deterministic harness. They demonstrate event logging and analysis flow, **not** that ML improves performance. The matching values are expected for a single short run with early fallback/cold-start behavior.

### 4.6 Controlled paired development-model result (not letter evidence)

The former 12-round smoke run was replaced by a 30-paired-seed, 300-round controlled development-model run at density 60, with the first 60 rounds excluded as ML warm-up. The analysis now treats each post-warm-up **seed/run** as one independent observation rather than treating individual rounds as independent samples.

The controlled model gives different post-warm-up values: ML has lower mean latency (227.64 vs. 249.01 ms), higher PDR (0.321 vs. 0.220), and higher throughput (2.542 vs. 0.178 packets/round) than its paired static counterpart. These values validate that the implementation can generate a policy-dependent paired comparison after the model leaves fallback.

They are **not research results and must not appear in Section VI**. Their purpose is to validate the experiment plumbing. The model contains synthetic reliability/congestion dynamics, so the same workflow must be run with measured SUMO/Veins/OMNeT++ events before the letter claims an ML advantage.

---

## 5. Complete paper outline and evidence plan

### 5.1 Intended title

**Formally Verified, ML-Adaptive AGS-PBFT for Quantum-Resilient CAV Communication**

Alternative: **Closing the Verification and Adaptivity Gaps in PQC-Blockchain CAV Security: A Crypto-Agile, ML-Predictive AGS-PBFT with Formal Guarantees**.

### 5.2 Letter narrative

The letter must make a narrow and defensible claim:

> We replace an underspecified KEM/signature use and static grouping heuristic with a standard-compliant ML-KEM/ML-DSA protocol, a lightweight predictive grouping policy with safe fallback, formal symbolic checks, and reproducible multi-seed evaluation.

The novelty is the **combination and rigor**, not invention of a new PQC primitive or ML architecture.

### 5.3 Four-page structure

| Section | Required content | Approx. budget |
| --- | --- | ---: |
| Abstract | Problem, gap, mechanisms, real headline result only | 0.15 page |
| I. Introduction | CAV/PQC motivation, exact base-paper gaps, at most four contributions | 0.40 page |
| II. System and threat model | Four-layer setting, Dolev–Yao adversary, PBFT fault assumption | 0.30 page |
| III. Crypto-agile registration and AKE | Credential, ephemeral ML-KEM, ML-DSA, key confirmation, suite IDs | 0.90 page |
| IV. ML-adaptive AGS-PBFT | Features, predictor, membership policy, fallback | 0.55 page |
| V. Formal verification | Assumptions, game-hop sketch, ProVerif properties and boundaries | 0.70 page |
| VI. Evaluation | Multi-seed method, ablation, best-static comparison, crypto overhead | 0.75 page |
| VII. Conclusion | Concrete contribution and bounded future work | 0.15 page |

### 5.4 Figures and tables

1. Registration-plus-AKE sequence diagram.
2. Feature -> online predictor -> reliability/congestion -> group-decision/fallback diagram.
3. Formal-properties table: secrecy/authentication/replay/assumptions/boundaries.
4. ML versus best-static results with 95% confidence intervals across densities and network conditions.
5. Crypto-overhead table: actual ML-KEM/ML-DSA measurements and experimental Saber comparison, if a maintained Saber backend is added.

### 5.5 Required evaluation matrix

Vary each of the following with a documented scenario definition:

- Vehicle density.
- Mobility pattern and link quality.
- Traffic load.
- Packet-loss level.
- Byzantine-node fraction.
- Static score penalty, threshold multiplier, reassignment window, and group-size threshold.

Measure:

- End-to-end latency and consensus latency.
- Throughput and PDR.
- Control-byte/signature overhead.
- Actual crypto operation cost.
- Group churn rate.
- Malicious-node detection/removal time.
- Honest-node false-removal rate.

Statistics required for each final scenario: at least 30 paired untouched test seeds, mean, 95% CI, effect size, paired t-test or Wilcoxon after distribution checking, and repeated-measures ANOVA plus correction when comparing multiple densities/conditions.

---

## 6. Current reference knowledge

The curated, current 2025–2026 bibliography is in `references/Latest_CAV_PQC_Reference_Shortlist.md`.

The most useful reference roles are:

- **Direct baseline:** Aslam, Bhardwaj, and Chaudhary (2025).
- **Latest V2X PQC/AKA survey:** Wang and Tan (2026).
- **PQC IoV authentication:** Rasheed and Mostafa (2025); Mishra and Rewal (2025).
- **PQC vehicular blockchain:** Asim et al. (2026); Zhang, Cao, and Wang (2025).
- **AI/blockchain contextual work:** Okafor et al. (2026); Alluhaibi (2026).
- **Automotive deployment context:** Mohamed et al. (2026).
- **Standards/method:** NIST FIPS 203, FIPS 204, NIST CSWP 39, and Blanchet/ProVerif.

Keep the final letter to roughly 12–18 references. Recent does not automatically mean relevant: sources must support a concrete claim, baseline, method, or deployment constraint.

---

## 7. What remains before writing the letter

1. Install/configure SUMO, Veins, and OMNeT++ or an equivalent accepted simulator and implement the final adapter.
2. Validate the static baseline qualitatively against the source-paper scenario without copying its claimed numbers.
3. Lock a train/validation/test seed list.
4. Run static ablation; select one best-static configuration before comparing ML.
5. Run at least 30 paired test seeds per scenario and generate the final CSVs/figures.
6. Add a maintained experimental Saber backend only if it is needed and can be reproduced; otherwise omit it from results.
7. Extend ProVerif to the final complete protocol model and write the ROR-style computational proof sketch with explicit assumptions.
8. Draft the paper only from logged, generated results; never hand-enter or estimate numbers.
9. Perform independent crypto, networking, and ML/statistics review before submission.

## 8. Non-negotiable writing constraints

- Never call ML-KEM a signature scheme or call ML-DSA a KEM.
- Never claim a development-harness value is a SUMO/Veins/OMNeT++ result.
- Never state base-paper values as our values.
- Never claim formal verification proves code security, side-channel security, or real-world availability.
- Never claim ML superiority until it beats the best ablated static policy on untouched paired test seeds with uncertainty/statistical reporting.
- Never claim crypto-agility without explicit algorithm identifiers and a valid replacement path.
