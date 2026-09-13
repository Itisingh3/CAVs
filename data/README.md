# External data boundary and canonical reliability windows

This project does **not** claim that a public CAN intrusion corpus is a CAV
blockchain or V2X data set.  In particular, no public CAN corpus contains
TA credentials, RSU/MEC membership, signed PBFT votes, or ground-truth
Byzantine consensus behaviour.  Those fields must be collected from the
instrumented CAV implementation before a complete grouping claim is made.

## Selected external source: ROAD

The external training source is the **Real ORNL Automotive Dynamometer
(ROAD) CAN Intrusion Dataset**, release 10462796 at Zenodo.  It contains real
automotive CAN recordings and documented injected attacks.  It is used only
to train/evaluate the automotive temporal intrusion-probability branch
`P_ML`; it is not reported as an AGS-PBFT networking experiment.  Keep the
unmodified archive outside version control under `data/raw/ROAD/` and retain
its Zenodo metadata and checksum.

## Canonical input for the full reliability layer

After protocol instrumentation is available, create
`data/derived/cav_reliability_windows.csv` with one *causal* row per node and
window.  Required columns are:

```
split,scenario_id,node_id,window_index,reliable,
agreement_rate,normalized_rtt,pdr,link_quality,score_trend,recent_fault_rate,
velocity_stability,consensus_participation,historical_reputation,credential_trust
```

All feature columns are normalized to `[0,1]`; a larger value means stronger
reliability evidence except `normalized_rtt` and `recent_fault_rate`.  A row
must be emitted before its `reliable` outcome is revealed.  Split by complete
scenario/node trace (never random rows): train for fitting, validation for
model/threshold/calibration selection, and a locked test set for one final
evaluation.  The label must come from an independently logged consensus or
security outcome, never from a feature or the predictor being evaluated.

The paper must name the ROAD result an *external automotive intrusion
benchmark* and reserve ML-adaptive AGS-PBFT statements for the above
protocol-telemetry data.

For every candidate report precision, recall, accuracy, F1, AUROC, AUPRC, and
the complete confusion matrix.  Treat an unreliable node selected as reliable
as a false-trust error, and a reliable node excluded from the consensus group
as a false-removal error.  Report neither as a networking latency or delivery
result unless the underlying trace actually measured it.
