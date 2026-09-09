# Outline v4: "Crypto-Agile, ML-Adaptive AGS-PBFT for Quantum-Resilient CAV Communication"
### Changes from v2: single-model → multi-ML comparison | added signature-selection rationale | numeric lit-comparison → qualitative capability table | tighter, delta-only prose
### Note: v3 proposed swapping ProVerif → Scyther. Decision: **keep ProVerif** — its `phase`-based forward-secrecy idiom is standard and already implemented in `formal/secrecy_equivalence.pv`; Scyther has no equivalent native construct for compromise-scenario forward secrecy and would require hand-rolled extra roles, which is more error-prone for the property that matters most here.

---

## 0. Letter Discipline (new)

This is a **letter**, not a survey. Every paragraph must answer "why does this need to exist." Cut anything a reader could get from citing the base paper. Budget stays ~4 pages, 4-5 figures/tables.

**Non-negotiable carry-overs from the project knowledge base:**
- Never present development-harness numbers as SUMO/Veins/OMNeT++ results.
- Never state a base-paper or other-paper's numeric result as a comparison baseline for your own numbers — use your own best-ablated-static as the only numeric baseline.
- ML claims require untouched paired test seeds with CI + significance testing.

---

## 1. Introduction (0.35p, was 0.4p)

- 1 sentence: CAVs + quantum threat (cite base paper, don't re-derive).
- 1 short paragraph: **why CAVs specifically** — safety-critical, latency-sensitive, multi-stakeholder trust (no single authority a vehicle/RSU/MEC operator all trust equally), which is exactly why blockchain-consensus + PQC co-occur here and not in, say, plain TLS deployments.
- Gap statement: quote base paper's own future-work line on ML-adaptivity; name the undefined-signature gap.
- Contributions (4 max, one line each): (i) ML-DSA-authenticated protocol replacing hash tokens, with an explicit primitive-selection rationale; (ii) Scyther-verified security claims including forward secrecy/KCI under compromise rules; (iii) multi-algorithm ML grouping predictor with accuracy/F1/AUROC comparison, safe fallback; (iv) multi-seed, ablation-grounded evaluation.

---

## 2. System & Threat Model (0.3p) — unchanged from v2

Four-layer architecture (cite, don't redraw), Dolev-Yao adversary, PBFT `n>=3f+1` bound, signature-forgery adversary added.

---

## 3. Crypto-Agile Protocol: Registration & AKE (0.85p)

### 3.1 Primitive layer + **signature-selection rationale (NEW, ~100 words)**
State the abstract `KEM`/`SIG` interface as before, then justify ML-DSA-65 explicitly against the two live alternatives:
- **Falcon:** smaller/faster-verify signatures, but floating-point signing and Gaussian-sampling side-channel risk make it a harder OBU deployment target.
- **SPHINCS+:** conservative hash-based assumption, but large signatures and slow signing are a poor fit for a protocol that signs every consensus message.
- **ML-DSA:** shares the module-lattice hardness family with ML-KEM — one assumption class, one library, a cleaner crypto-agility story than mixing families. This is a design decision, not a benchmark win — say so plainly (Dilithium is not the fastest option; it's the most coherent one for this deployment).

### 3.2 Registration (unchanged from v2 §3.2) — TA-signed bundle replacing the hash token.

### 3.3 AKE (unchanged from v2 §3.3) — sign-before-encapsulate, verified before proceeding.

### 3.4 Full AKE protocol notation (NEW — moved up from an appendix-style afterthought)
Write out the message flow with full crypto notation in-line (not just prose), matching `spec/notation.md` and `spec/ake.md`:

```
I -> R : sid, n_I, ts, kem_alg, sig_alg, pk_I, cred_I, sig_I = Sign(sk_I, m1)
R -> I : sid, n_I, n_R, ts, ct = Encap(pk_I, ss), cred_R, sig_R = Sign(sk_R, m2)
I      : ss = Decap(sk_I, ct); th = H(m1||sig_I||m2||sig_R); K_s = H("CAV-AKE-v1"||ss||th)
I -> R : sid, th, tag = HMAC(K_s, "initiator-confirm"||th), sig_I' = Sign(sk_I, m3)
R      : verify sig_I'; recompute th, K_s; check tag; accept
```
This block *is* the protocol figure's caption text — reuse it directly as Figure 1's annotation.

### 3.5 Consensus-layer signing — unchanged from v2 §3.4.

---

## 4. ML-Adaptive AGS-PBFT Grouping (0.6p)

### 4.1 What it replaces — unchanged (fixed +1/-5, μ±σ, fixed cadence).

### 4.2 Multi-algorithm predictor (CHANGED from v2, updated)
Same six-feature vector (`agreement_rate, normalized_rtt, pdr, link_quality, score_trend, recent_fault_rate`). Compare, on train/validation seeds only, four algorithms spanning the lightweight-to-heavier spectrum:
- **Logistic Regression** (existing online baseline — cheapest, incremental, linear decision boundary)
- **Decision Tree** (single shallow tree — cheap to evaluate, interpretable, captures simple nonlinear splits)
- **Ensemble method** (Random Forest or Gradient-Boosted Trees — captures nonlinearity and feature interactions; note in the letter that only the *trained* ensemble's inference cost matters for OBU deployment, training itself is offline)
- **MLP** (single hidden layer — upper bound of what's still "lightweight," used to show diminishing returns relative to the added complexity)

### 4.2.1 Metrics — confusion-matrix definitions (mapped from the standard testing/condition table)
Adapt the standard confusion-matrix framework directly to this problem, relabeling condition/test in terms of node reliability rather than the shaded/unshaded template it's usually drawn for:

| | Condition positive (actually reliable) | Condition negative (actually unreliable) |
|---|---|---|
| **Test positive** (predicted reliable) | True positive `T_p` — correct | False positive `F_p` — incorrect |
| **Test negative** (predicted unreliable) | False negative `F_n` — incorrect | True negative `T_n` — correct |

From this 2x2 table:
- **Precision / PPV** = `T_p / (T_p + F_p) × 100%` — of the nodes the model calls reliable, how many actually are.
- **Recall / Sensitivity (RR)** = `T_p / (T_p + F_n) × 100%` — of the actually-reliable nodes, how many the model catches.
- **Specificity (SR)** = `T_n / (T_n + F_p) × 100%` — of the actually-unreliable nodes, how many the model correctly flags.
- **NPV** = `T_n / (T_n + F_n) × 100` — of the nodes the model calls unreliable, how many actually are.
- **Accuracy** = `(T_p + T_n) / (T_p + F_p + F_n + T_n) × 100%`.
- **F1** = `2 × (Precision × Recall) / (Precision + Recall)` — harmonic mean, the metric that matters most here since reliable/unreliable nodes are imbalanced and accuracy alone would be misleading (a model that always predicts "reliable" scores high accuracy but zero recall on malicious nodes).
- **AUROC** = area under the curve of true-positive rate (Recall) vs. false-positive rate (`1 − Specificity`) swept across the model's probability threshold — the one metric that's threshold-independent, useful since the actual deployment threshold is set by the fallback-guard confidence rule (§4.3), not by the 0.5 default.

Report **all five of precision, recall, accuracy, F1, and AUROC** per algorithm — this is a deliberate widening from the v3 accuracy/F1/AUROC-only set, since precision/recall separately (not just their F1 blend) tells a reviewer *which kind* of error each algorithm is prone to (falsely trusting a malicious node vs. falsely ejecting an honest one — the latter is exactly the "honest false-removal rate" metric already tracked in your evaluation matrix, so this ties directly into existing infrastructure). One grouped bar chart, four algorithms × five metrics — this is Figure 2.

State explicitly: whichever algorithm wins, **inference-time cost stays OBU-appropriate** — the comparison is about predictive quality; the latency constraint is separate and already satisfied by all four at inference time.

### 4.3 Integration + fallback — unchanged from v2 (best-model's output replaces the μ±σ decision; fallback guard unchanged).

### 4.4 What NOT to attempt — unchanged from v2 (no novel ML architecture claim, no regret-bound derivation).

---

## 5. Formal Security Verification — ProVerif (0.7p) — unchanged from v2, retained

### 5.1 ROR proof sketch — unchanged from v2 §5.1 (game hops G0–G3, final theorem bounding `Adv^{AKE}` by ML-DSA EUF-CMA, KEM IND-CCA2, and the birthday bound).

### 5.2 ProVerif model — unchanged from v2 §5.2, matches the existing `formal/model.pv` and `formal/secrecy_equivalence.pv`:
- Processes `TA`, `CAV`/Initiator, `RSU`/Responder, composed with `!` for unbounded sessions.
- Queries and the attack class each one rules out:

| ProVerif query | Attack class covered |
|---|---|
| `query attacker(sessionKey)` | Eavesdropping / session-key disclosure |
| `query attacker(sk_CAV)` / `sk_RSU` | Long-term key disclosure |
| Injective correspondence `AcceptedByCAV ==> InitiatedByRSU` | Impersonation, MITM, replay |
| `phase 1` long-term key leak + phase-0 session-key secrecy | Forward secrecy under long-term key compromise — this is the property ProVerif's `phase` construct handles natively and cleanly; it's the reason ProVerif stays the tool of record here |

- Note the existing model split: `model.pv` covers correspondence/authentication, `secrecy_equivalence.pv` isolates the ephemeral-KEM/KDF observational-equivalence secrecy check. Both must be extended to the *final* frozen spec before the letter's numbers are locked — see `PROJECT_KNOWLEDGE_BASE.md` §4.4 boundary notes (symbolic-model checks only, not implementation or side-channel security — say this explicitly in the letter).
- Deliver one verified-properties table (property x checkmark/x x notes) — same payoff-figure role as before, Figure/Table 3.

---

## 6. Evaluation (0.75p)

### 6.1 Multi-seed methodology — unchanged (>=30 seeds, mean±CI, paired t-test/Wilcoxon, ANOVA+Bonferroni across densities).

### 6.2 Hyperparameter ablation → best-static control — unchanged from v2 §6.2.

### 6.3 ML predictor comparison — NEW, replaces part of old §6.3
The precision/recall/accuracy/F1/AUROC grouped bar chart from §4.2 (four algorithms: Logistic Regression, Decision Tree, ensemble, MLP), generated from train/validation seeds; the winning predictor (by F1 or AUROC, not raw accuracy, given class imbalance) is what's carried into the ML-vs-best-static latency/throughput comparison on untouched test seeds.

### 6.4 Crypto-agility comparison table — unchanged from v2 §6.3 (Kyber/Saber, ML-DSA overhead vs. hash-token, be honest about the overhead).

### 6.5 Related-work comparison — CHANGED (numeric → qualitative)
One table: your letter vs. the shortlist papers, columns = {signature scheme, KEM, formal method + properties proven, ML-adaptive: Y/N, multi-seed statistics: Y/N}. **No cross-paper numeric latency/throughput comparison** — different simulators and configurations make that comparison unsound, and it conflicts with the project's own "never borrow another paper's numbers as your baseline" rule. Numeric superiority claims stay confined to your own ML-vs-best-static result.

---

## 7. Conclusion & Future Work (0.15p) — unchanged, add Scyther-model extension and further ML algorithms as future work lines.

---

## 8. Figures/Tables Budget (5 total)
1. AKE sequence diagram, annotated with the §3.4 notation block.
2. ML predictor comparison chart (accuracy/F1/AUROC across algorithms).
3. ProVerif verified-properties table (query → attack class → pass/fail).
4. ML-adaptive vs. best-ablated-static — latency/throughput/detection-time, multi-seed CI (your only numeric superiority claim).
5. Crypto-agility overhead table (Kyber/Saber, ML-DSA vs. hash-token) **or** the qualitative related-work capability table — pick one, not both, to stay in budget.

---

## 9. Immediate Next Steps
1. Extend `formal/model.pv` and `formal/secrecy_equivalence.pv` to the final frozen spec (full credential + replay-cache processes, not just the isolated KEM/KDF core) before any paper claim is made — the isolation warning already in `secrecy_equivalence.pv` still applies.
2. Extend `ml/predictor.py` with a `DecisionTreeReliability`, an ensemble model (Random Forest or Gradient-Boosted Trees), and a minimal MLP, all behind the same interface as `OnlineLogisticReliability`, so `ags_pbft_ml.py` doesn't need to change.
3. Add an offline train/validation harness that reports precision, recall, accuracy, F1, and AUROC per model (confusion-matrix-derived, per §4.2.1), keeping test seeds untouched.
4. Draft §3.1's signature-rationale paragraph now — it's self-contained and doesn't depend on any pending experiment.
5. Build the related-work capability table from the existing reference shortlist; no new sources needed.
