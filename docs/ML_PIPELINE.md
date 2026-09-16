# ML pipeline and data boundary

There are two deliberately separate experiments.

1. **ROAD CAN intrusion:** `python -m data.preprocess_road` creates causal
   automotive-CAN windows with `intrusion` as the target. These results are
   automotive IDS results only.
2. **CAV reliability:** `python -m ml.train` consumes instrumented CAV
   telemetry containing the canonical ten reliability inputs and `reliable`.
   It is the only input permitted to influence dynamic AGS-PBFT grouping.

For recurrent candidates, rows are grouped by `(split, scenario_id, node_id)`
and ordered by `window_index`. The target `y(t)` is paired with
`X(t-K+1:t)`, whose exact shape is `[samples, sequence_length, 10]`. A trace
appearing in more than one split is rejected. Validation selects a model; the
locked test split is read only with `--evaluate-locked-test`.

The model returns `P_ML = P(reliable | available evidence)`. It is then an
input to `LearnedReliabilityScore`, along with separately derived historical,
consensus, and network evidence. The score learns its four coefficients on
validation data; it is not a hand-tuned weighting rule.

LSTM, GRU, and BiLSTM are offline comparisons. Even BiLSTM receives only the
causal window ending at `t`; production decisions must never be built from a
window containing observations after `t`.

The dependency-free decision tree and random forest are bounded online-control
baselines. For large exported traces their offline fitting uses a deterministic
evenly spaced 256-window reservoir, avoiding repeated quadratic retraining.
