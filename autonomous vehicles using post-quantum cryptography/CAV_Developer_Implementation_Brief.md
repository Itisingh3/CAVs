# Developer Implementation Brief
## Crypto-Agile, ML-Predictive AGS-PBFT for Quantum-Resilient CAV Communication

Hand this document to your developer (or paste it into Claude Code / an engineering assistant) as the primary spec. It fixes terminology, tech choices, module boundaries, and acceptance criteria so the resulting code, ProVerif model, and paper stay consistent with each other.

---

## 0. Non-Negotiable Naming/Design Decisions (lock these first)

- Use **ML-KEM-768** (not "Kyber") for key encapsulation. NIST FIPS 203.
- Use **ML-DSA-65** (not "Dilithium") for all digital signatures. NIST FIPS 204.
- **Saber** is an experimental alternate KEM backend only — not a co-default, not benchmarked with the same rigor as ML-KEM. Label every Saber result "experimental" in code comments, logs, and output tables.
- Do **not** hand-roll any cryptographic primitive. Use a maintained library only (see §2).
- Baseline AGS-PBFT parameters must exactly match the base paper: initial score 100, `+1` on agreement, `−5` on disagreement, `μ±σ` thresholds, reassignment every 50 requests. Any deviation invalidates the comparison.

---

## 1. Repository Structure

```
cav-pqc-agsbft/
├── spec/                     # Frozen protocol specification (write BEFORE code)
│   ├── notation.md
│   ├── registration.md
│   ├── ake.md
│   ├── consensus_signing.md
│   ├── ml_grouping_interface.md
│   └── state_machines.md
├── crypto/                   # Crypto-agility layer
│   ├── suite_interface.py    # KeyGen/Encap/Decap/Sign/Verify abstract interface
│   ├── mlkem_backend.py
│   ├── mldsa_backend.py
│   └── saber_backend.py      # experimental, clearly flagged
├── protocol/                 # Registration + AKE + consensus message handling
│   ├── registration.py
│   ├── ake.py
│   └── consensus_messages.py
├── consensus/
│   ├── ags_pbft_baseline.py  # faithful reproduction of base paper
│   └── ags_pbft_ml.py        # ML-adaptive variant
├── ml/
│   ├── features.py
│   ├── predictor.py          # online logistic regression / EWMA
│   └── fallback_guard.py     # low-confidence -> revert to best static policy
├── sim/                      # SUMO/Veins/OMNeT++ integration
│   ├── scenarios/
│   ├── seed_manager.py       # train/val/test seed separation
│   └── run_experiment.py
├── analysis/
│   ├── ablation_sweep.py
│   ├── stats.py              # CI, paired t-test / Wilcoxon, ANOVA+Bonferroni
│   └── generate_figures.py
├── formal/
│   └── model.pv              # ProVerif model of the FINAL protocol
├── tests/
│   ├── test_crypto_unit.py   # forged sigs, replay, corrupted ciphertext, expired cred
│   ├── test_protocol.py
│   └── test_consensus.py
├── results/                  # versioned raw logs + CSV/JSON, never hand-edited
└── README.md                 # exact repro steps: env, seeds, commands
```

---

## 2. Cryptographic Layer — Required Libraries

- **liboqs** (Open Quantum Safe) with Python bindings (`liboqs-python`) or **PQClean** — both provide maintained ML-KEM-768 and ML-DSA-65 implementations. Do not implement lattice math yourself.
- For Saber (experimental only): PQClean's Saber implementation, clearly isolated behind the same `suite_interface`.
- Define one interface all three backends implement:
  ```
  KeyGen() -> (pk, sk)
  Encap(pk) -> (ct, ss)          # ML-KEM / Saber only
  Decap(sk, ct) -> ss            # ML-KEM / Saber only
  Sign(sk, msg) -> sig           # ML-DSA only
  Verify(pk, msg, sig) -> bool   # ML-DSA only
  ```
- Every protocol message carries an explicit **algorithm identifier** field so the suite is negotiable, not hardcoded.

**Acceptance criteria:** unit tests pass for (a) valid registration/AKE flow, (b) forged ML-DSA signature rejected, (c) replayed message rejected via nonce/timestamp check, (d) corrupted ML-KEM ciphertext causes decap failure handled gracefully, (e) expired credential rejected. Also benchmark and log: keygen/encap/decap/sign/verify latency, and key/ciphertext/signature sizes, on the actual experiment machine (not literature numbers).

---

## 3. Protocol Specification (write and freeze before any simulation code)

Deliverables in `spec/`:
- **Notation table**: every symbol used in registration, AKE, and consensus signing.
- **Registration**: TA-signed pseudonymous credential issuance. TA generates `(pk_KEM, sk_KEM)` via ML-KEM and `(pk_sig, sk_sig)` via ML-DSA per entity; TA signs the full bundle `σ_TA = ML-DSA.Sign(sk_TA, S_i ‖ pk_KEM_i ‖ pk_sig_i)`.
- **AKE**: sender signs `(pk_KEM ‖ S_i ‖ TS)` with ML-DSA before ML-KEM encapsulation; receiver verifies signature before proceeding; explicit key-confirmation step; session identifiers and nonces defined precisely enough to rule out replay.
- **Consensus signing**: `PRE-PREPARE`/`PREPARE`/`RESPONSE` all ML-DSA-signed, replacing the base paper's undefined `Sign_l`/`Sign_r`/`Sign_c`.
- **ML grouping interface**: exact inputs (feature vector), prediction target (node-reliability probability, aggregate congestion level), update schedule (per window), candidate/consensus selection policy, and the safe-fallback rule (low model confidence → revert to best-ablated static policy).
- **State machines + abort/failure rules**: what happens on signature failure, decap failure, timeout, malformed message — define explicitly, don't leave implicit.

**This spec is the single source of truth.** Code, the ProVerif model, and the paper's protocol section must all describe exactly this and nothing else — no silent drift.

---

## 4. Baseline AGS-PBFT (implement and validate before touching ML)

- Reproduce the base paper's scoring/reassignment rules exactly, with every parameter (score deltas, threshold multiplier, window size, group-size policy) exposed as a config value, not a hardcoded constant.
- Log every consensus round, score update, group transition, injected fault, and network event to structured output (CSV/JSON) — this log format is what the ablation sweep and later ML comparison both consume.
- **Acceptance criteria:** baseline reproduces qualitatively similar behavior/order-of-magnitude metrics to the base paper's reported results under equivalent settings, before you trust it as your comparison point.

---

## 5. ML-Adaptive Grouping

- Model: **online logistic regression or EWMA only** — explicitly reject deep learning here; this is a stated design constraint tied to OBU compute limits, not a shortcut.
- Features per node per window: recent consensus-agreement rate, RTT, packet delivery ratio, mobility/link-quality signal (from Veins), score trend over last *k* windows, recent fault indicators.
- Outputs: predicted node-reliability probability → feeds group membership decision; predicted aggregate congestion → feeds group-size policy.
- **Fallback guard is mandatory**: when model confidence is below a defined threshold, the system must provably revert to the best-ablated static policy (§7). Log every fallback trigger — this becomes a robustness talking point in the paper.

---

## 6. Simulation Pipeline

- Integrate into SUMO/Veins/OMNeT++ (same toolchain as the base paper, for comparability) or a documented equivalent.
- Vary: vehicle density, mobility pattern, traffic load, packet-loss level, Byzantine-node fraction.
- **Seed discipline (critical):** split seeds into training / validation / untouched test sets up front. The ML model is pretrained/tuned only on training+validation seeds. Final reported numbers use only the untouched test seeds. Document this split in the README — reviewers will check for leakage.
- Every run stores: full config, code commit hash, random seed, raw event logs, environment info (library versions, OS). Nothing goes into a figure without a traceable run behind it.

---

## 7. Ablation + Statistical Evaluation

- Sweep static baseline hyperparameters first: score penalty asymmetry, `μ±kσ` threshold multiplier, reassignment window size, group-size thresholds.
- Select the single **best-performing static configuration** — this becomes your ML baseline, not the base paper's unablated default.
- Run **≥30 paired test seeds** per scenario (same seeds across static-best and ML-adaptive for valid pairing).
- Report: mean, 95% CI, effect size (e.g., Cohen's d), and the appropriate significance test — paired t-test if approximately normal, Wilcoxon signed-rank otherwise; repeated-measures ANOVA + Bonferroni if comparing across more than two conditions (e.g., multiple densities).
- Metrics to capture: end-to-end latency, consensus latency, throughput, PDR, control/signature overhead, crypto cost (from §2 benchmarks), group churn rate, malicious-node detection/removal time, and false-removal rate of honest nodes.

---

## 8. Formal Verification

- Model the **final, frozen** protocol from §3 in ProVerif — not an earlier draft. If the spec changes, the model must be rebuilt.
- Queries required: session-key secrecy, long-term key secrecy, injective correspondence for mutual authentication (replay resistance), forward secrecy under `phase 1` long-term key compromise.
- Deliver a computational proof sketch (ROR-style game hops) alongside the ProVerif output, with explicit stated assumptions: ML-KEM IND-CCA2 hardness, ML-DSA EUF-CMA hardness, hash/KDF modeled as random oracle, and how the authenticated-KEM composition is argued.
- **Calibrate claims in the writeup:** ProVerif proves symbolic-model properties, not implementation security or timing-channel resistance — say this explicitly rather than overclaiming.

---

## 9. Output Deliverables Developer Must Hand Back (mapped to paper assets)

| Deliverable | Paper use |
|---|---|
| One protocol sequence diagram (data, not hand-drawn) or the data to build one | Section III figure |
| ML-grouping architecture diagram data (feature → prediction → decision) | Section IV figure |
| ProVerif verified-properties table (CSV) | Section V table |
| Ablation sweep results + ML-vs-best-static comparison, with CI (CSV + plotting script) | Section VI figure |
| Crypto-agility benchmark table: ML-KEM vs. Saber (experimental), ML-DSA overhead vs. base paper's hash-token cost (CSV) | Section VI table |
| Full reproducibility package: scripts that regenerate every figure/table from raw logs, README with exact commands | Supplementary / reviewer request |

**Hard rule for the developer:** no number goes into the paper unless it's generated by a script from a logged run. Do not hand-type or estimate results.

---

## 10. Suggested Build Order (dependency-driven, not calendar-driven)

1. Freeze `spec/` (§3)
2. Crypto layer + unit tests (§2)
3. Baseline AGS-PBFT + validate against base paper behavior (§4)
4. Simulation pipeline + seed split (§6)
5. Static hyperparameter ablation, lock in "best static" (§7, first half)
6. ML-adaptive grouping + fallback guard (§5)
7. Full statistical comparison, ML vs. best-static (§7, second half)
8. ProVerif model of the frozen spec + proof sketch (§8)
9. Figure/table generation scripts (§9)
10. Only then: write the letter, using real numbers throughout

---

## 11. Review Gate Before Submission

Have the finished implementation + draft reviewed from three angles before writing the final version of the letter:
- **Cryptography reviewer**: correctness of ML-KEM/ML-DSA usage, ROR game hops, ProVerif model fidelity to the frozen spec.
- **Vehicular networking reviewer**: simulation realism, baseline fidelity, metric definitions.
- **ML/statistics reviewer**: feature leakage check (train/val/test seed separation), significance testing correctness, effect sizes reported not just p-values.
