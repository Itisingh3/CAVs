# Outline & Architecture (v2): "Crypto-Agile, ML-Predictive AGS-PBFT for Quantum-Resilient CAV Communication"
### Scoped to: Protocol (Reg+AKE) → ROR/ProVerif → Crypto-agility (Dilithium/Saber) + ML-adaptive grouping → Multi-seed stats → Hyperparameter ablation

---

## 0. Scope Sanity Check

Your 5 points are really **6 deliverables** (point 3 bundles crypto-agility + ML-adaptive grouping). For a true 4-page letter (~3,000-3,500 words, 4-5 figures/tables total), this is achievable **only if**:

- Points 1 + half of 3 (Dilithium signatures, Saber as alt KEM) are merged into **one** "crypto-agile protocol" contribution — don't design/evaluate them as separate pieces
- The ML component stays **lightweight** (online logistic regression, EWMA, or a shallow decision tree over a handful of features) — not a deep model. This is a *feature*, not a limitation: it matches the low-latency/low-compute reality of OBUs, which is a claim you can make explicitly in the letter
- Hyperparameter ablation (point 5) doubles as your **baseline comparison for the ML predictor** — i.e., "static μ±σ with best-ablated hyperparameters" becomes the control condition your ML-adaptive version is compared against. This means point 5 doesn't need its own separate experiment; it's the justification for why ML is needed, folded into the same results section as point 3's evaluation

With that consolidation, this fits in 4 pages. Budget below reflects it.

---

## 1. Novelty Analysis

| Base paper gap | Your fix | Novelty |
|---|---|---|
| `Sign_c/Sign_l/Sign_r` are undefined hash tokens, not real signatures — no non-repudiation, no formal unforgeability guarantee | Concrete Dilithium instantiation for all consensus-layer signing + registration signing | Medium-high — closes a real, specific gap you can name explicitly |
| Protocol is hard-coded to Kyber only; no path to swap primitives if Kyber is later deprecated/attacked (a real NIST-agility concern) | Crypto-agile design: KEM slot supports Kyber **or** Saber behind a common interface; one comparison table (latency/key-size/computation) | Medium — not a new primitive, but a genuine, citable engineering contribution; NIST itself recommends crypto-agility as a migration best practice |
| No formal proof — only prose walk-through of Kyber's known properties | ROR game-based proof + ProVerif symbolic model of the **full composed** protocol (registration + AKE + consensus signing) | **High** — this remains your strongest claim, unchanged from before |
| AGS-PBFT grouping uses static μ±σ thresholds and fixed +1/−5 scoring, unjustified and non-adaptive to actual network conditions — **the base paper's own authors name this as future work** ("integrating ML... to predict and adapt to dynamic network conditions in real-time") | Lightweight online predictor (features: recent latency, PDR, mobility/link-quality from Veins, score trend) forecasts network condition and drives dynamic group-size + reassignment-window decisions, replacing the static rule | **High** — you are directly and explicitly fulfilling a gap the original authors themselves flagged. This is the cleanest "delta" claim in the whole letter — cite their exact sentence in your intro |
| Single-run simulation, no variance reported | ≥30-seed runs, mean±CI, significance testing | Low novelty, high rigor — expected baseline now, not optional |
| Scoring hyperparameters asserted without justification | Ablation sweep, used as the **control condition** against your ML predictor | Low novelty alone, but essential — it's what makes your ML claim credible rather than anecdotal |

**Overall framing for your introduction:** *"[Base paper] explicitly identifies two open problems: (i) the absence of formal verification, and (ii) the potential for ML-based prediction to replace static consensus-grouping heuristics. This letter addresses both, while also hardening the protocol's signature scheme and demonstrating crypto-agility across NIST PQC finalists."* That's a tight, non-oversold novelty statement appropriate for a letter.

### Suggested title
*"Closing the Verification and Adaptivity Gaps in PQC-Blockchain CAV Security: A Crypto-Agile, ML-Predictive AGS-PBFT with Formal Guarantees"*

(Shorter alt: *"Formally Verified, ML-Adaptive AGS-PBFT for Quantum-Resilient CAV Communication"*)

---

## 2. Section-by-Section Outline (4 pages)

| Section | Content | Budget |
|---|---|---|
| Title/Abstract | ~150 words: name the two gaps you're closing (explicitly quote/paraphrase base paper's future-work sentence), state your 3 mechanisms (Dilithium signing, ML-adaptive grouping, ROR/ProVerif) and headline result | 0.15p |
| **I. Introduction** | Para 1: CAV+quantum threat (1-2 sentences, cite base paper, don't re-derive). Para 2: explicit gap statement — quote/cite the base paper's own future-work line on ML-adaptivity, plus the missing-formal-proof gap. Para 3: contribution bullets (4 max) | 0.4p |
| **II. System & Threat Model** | One compact paragraph reusing the base paper's 4-layer architecture (cite figure, don't redraw unless needed) + Dolev-Yao adversary definition for the formal model + signature-forgery adversary added to threat model | 0.3p |
| **III. Crypto-Agile Protocol: Registration & AKE** | Core section — see §3 below | 0.9p |
| **IV. ML-Adaptive AGS-PBFT Grouping** | Core section — see §4 below | 0.55p |
| **V. Formal Security Verification** | ROR proof sketch (theorem + game hops) + ProVerif model summary + verified-properties table | 0.7p |
| **VI. Performance Evaluation** | Multi-seed methodology, ML-vs-static ablation (this is where hyperparameter ablation lives), crypto-agility comparison table (Kyber vs. Saber, Dilithium overhead vs. base paper's hash-token) | 0.75p |
| **VII. Conclusion & Future Work** | 2-3 sentences; future work: larger-scale ML model, real hardware validation, Sybil/strategic-adversary game theory, Falcon as further alternative | 0.15p |

Total ≈ 3.9p of content + references (letters typically allow references to slightly extend beyond the page count, confirm venue rules).

**Figures/tables budget (4-5 total, no more):**
1. Sequence diagram: registration + AKE with Dilithium signing step highlighted (Section III)
2. Diagram/flowchart: ML predictor → feature vector → grouping decision, inline with AGS-PBFT pipeline (Section IV)
3. Table: ROR/ProVerif verified-properties summary (Section V)
4. Figure: ML-adaptive vs. best-ablated-static grouping — latency/throughput/malicious-node-detection-time under varying network conditions, multi-seed with CI (Section VI)
5. Table: crypto-agility comparison — Kyber vs. Saber (key/ciphertext size, encap/decap time) and Dilithium signature overhead vs. base paper's hash-token (Section VI)

---

## 3. Protocol Architecture (Section III)

### 3.1 Crypto-agile primitive layer
Define an abstract interface: `KEM.{KeyGen, Encap, Decap}` instantiated by **either** Kyber (ML-KEM) or Saber, and `SIG.{KeyGen, Sign, Verify}` instantiated by **Dilithium** (ML-DSA). State this as a design principle up front: the protocol logic (registration/AKE/consensus message flow) is primitive-agnostic; only the underlying KEM/SIG calls swap. This is what justifies calling it "crypto-agile" rather than just "we tested two algorithms."

### 3.2 Registration phase (extends base paper §5.2)
1. TA generates `(pk_KEM, sk_KEM)` via chosen KEM (Kyber or Saber) — unchanged in structure from base paper
2. **NEW:** TA additionally generates `(pk_sig, sk_sig)` via Dilithium
3. Registration token unchanged in form: `S_i = H(ID_i, pk_KEM_i, pk_sig_i, MK, TS_i)`
4. **NEW:** TA signs the full registration bundle: `σ_TA = SIG.Sign(sk_TA, S_i ‖ pk_KEM_i ‖ pk_sig_i)`. This is what the base paper is missing — their token is a hash, which authenticates *knowledge of MK* but provides no verifiable, non-repudiable signature an entity or auditor can check independently
5. Entity stores `(sk_KEM, sk_sig, S_i, σ_TA)`; verifies `σ_TA` against TA's known `pk_TA` before trusting the bundle

### 3.3 AKE phase (extends base paper Algorithm 1)
- KEM encapsulate/decapsulate flow kept structurally identical to base paper (this part was already reasonable)
- **NEW:** before encapsulation, sender signs `(pk_KEM ‖ S_i ‖ TS)` with Dilithium; receiver verifies signature **before** proceeding — this is the step that upgrades the protocol from "hash-authenticated" to "cryptographically authenticated," and is the exact claim your ROR/ProVerif model will verify (mutual authentication)

### 3.4 Consensus-layer signing (extends base paper Algorithm 2)
- `PRE-PREPARE`/`PREPARE`/`RESPONSE` messages signed with Dilithium instead of the base paper's undefined `Sign_l`/`Sign_r`/`Sign_c`
- No Merkle aggregation in this version (dropped per your revised scope) — keep this simple: state as a **future work** line that batch verification is a natural follow-up if signature-verification overhead becomes a bottleneck at scale

---

## 4. ML-Adaptive AGS-PBFT Grouping (Section IV)

This is your other headline contribution — spend real care here.

### 4.1 What it replaces
Base paper's rule: fixed score deltas (+1/−5), fixed reassignment cadence (every 50 requests), thresholds at μ±σ, and a hand-picked small/large group-size choice tied to "low activity" vs. "high activity" with no defined measurement of "activity."

### 4.2 Proposed mechanism
- **Features** (per node, per evaluation window): recent consensus-agreement rate, round-trip latency, packet delivery ratio, mobility/link-quality signal (available from Veins), score trend over last k windows
- **Model**: online logistic regression (or exponential-weighted moving average as an even simpler baseline variant) predicting `P(node reliable next window)`, retrained/updated incrementally each window at negligible cost — explicitly justify this choice as appropriate for OBU-class compute rather than defaulting to a heavier model
- **Integration point**: replace the fixed μ±σ threshold decision in Algorithm 2's "Score Update and Group Adjustment" procedure with the predicted reliability score; replace the fixed group-size choice with a prediction of aggregate network condition (e.g., predicted congestion level) mapping to a group-size policy (small group when predicted-low-activity, large group when predicted-high-activity) — this is a direct, mechanical replacement of two specific base-paper heuristics, which makes it easy to describe in limited space and easy to ablate against
- **Training data**: bootstrap from the same multi-seed simulation runs (offline pretraining on a held-out seed subset, online fine-tuning during evaluation) — be explicit about train/test seed separation to avoid leakage, reviewers will check this

### 4.3 What NOT to attempt in this letter
- No claim of a novel ML architecture — you're applying a standard lightweight online learner to a new problem instance, which is honest and sufficient
- No large-scale offline pretraining pipeline — keep the model and its description to a few sentences plus one small diagram
- Don't promise convergence/regret bounds unless you actually derive them — if you want a theoretical flourish, one sentence citing standard online-convex-optimization regret bounds for logistic regression is enough; do not attempt a novel proof here, it will blow your budget

---

## 5. Formal Verification Plan (Section V)

### 5.1 ROR proof sketch
- **G0**: real protocol, adversary advantage `Adv_0`
- **G1**: replace Dilithium signing with simulated oracle → `|Adv_0 - Adv_1| ≤ Adv^{EUF-CMA}_{Dilithium}`
- **G2**: replace KEM ciphertexts with simulated ones → `|Adv_1 - Adv_2| ≤ Adv^{IND-CCA2}_{KEM}` (state separately for Kyber/MLWE and Saber/MLWR hardness, one line each — this is a nice place to tie back to crypto-agility)
- **G3**: hash → random oracle, birthday bound `q_H^2/2^{l+1}`
- Final theorem: `Adv^{AKE} ≤ Adv^{EUF-CMA}_{Dilithium} + Adv^{IND-CCA2}_{KEM} + q_H^2/2^{l+1} + negl`
- Present as one theorem box + ~150 words, not a full derivation

### 5.2 ProVerif model
- Processes: `TA`, `CAV`, `RSU`, composed with `!` for unbounded sessions
- Primitives: `fun`/`reduc` pairs for KEM encap/decap, Dilithium sign/verify, hash
- Queries:
  1. `query attacker(sessionKey)` — session key secrecy
  2. `query attacker(sk_CAV)` / `sk_RSU` — long-term key secrecy
  3. Injective correspondence: `event AcceptedByCAV` implies preceding `event InitiatedByRSU` (mutual auth + replay resistance)
  4. Forward secrecy: `phase 1` long-term key leak, check phase-0 session keys remain secret
- Deliver as a single verified-properties table (property x checkmark/x x notes) — this is your Section V payoff figure

---

## 6. Evaluation Plan (Section VI)

### 6.1 Multi-seed statistical methodology
- >=30 seeds (SUMO trip seed + OMNET++ RNG seed varied together)
- Report mean +/- 95% CI for all latency/throughput/computation metrics
- Paired t-test (or Wilcoxon signed-rank if non-normal) between your method and each baseline **and** between ML-adaptive vs. best-ablated-static grouping
- If comparing across vehicle densities (multiple groups), use repeated-measures ANOVA with Bonferroni correction rather than stacking pairwise tests

### 6.2 Hyperparameter ablation -> becomes the ML control condition
- Sweep score-delta asymmetry (+1/-3, -5[default], -10) and threshold formulation (fixed, mu+/-0.5sigma, mu+/-sigma[default], mu+/-2sigma)
- Report the best-performing static configuration found — **this is your fair baseline**, not the base paper's unablated default, which strengthens your ML comparison's credibility (you're not just beating a strawman)
- One figure: static-ablation sweep results (2 small panels) + one clearly marked "best static" point, which then becomes a single reference line in the ML-comparison figure

### 6.3 Crypto-agility comparison
- One table: Kyber vs. Saber — public key/ciphertext size, encap/decap latency, and Dilithium's signature size/sign/verify time vs. the base paper's hash-token computation cost (be honest that Dilithium adds overhead vs. a bare hash — the value proposition is *security*, not speed, and you should say so explicitly rather than let a reviewer catch the tradeoff)

---

## 7. Immediate Next Steps

1. Pick KEM/SIG defaults now: **Kyber (primary) + Saber (comparison) for KEM, Dilithium for signatures** — lock this in before writing anything else
2. Draft Section III (protocol) first — the ROR/ProVerif model and the ML integration both depend on the exact message flow
3. Build the ProVerif `.pv` model in parallel — highest time cost, start immediately
4. Stand up the multi-seed simulation pipeline with CI computation *before* running full experiments, and reserve a held-out seed subset for ML pretraining vs. an untouched subset for final evaluation, so train/test separation is airtight from day one
5. Implement the static-hyperparameter ablation before the ML predictor — you need "best static" locked in as your baseline before you can honestly claim the ML version beats it
6. Write Introduction/Abstract last, once real numbers exist — especially the sentence quoting the base paper's own future-work line, which should be verbatim-accurate
