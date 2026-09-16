# Experiment protocol

- Freeze scenario/node-level train, validation, and locked-test partitions.
- Select candidates by validation F1/AUROC only; evaluate the selected model
  on the locked test once.
- Run seeds `42, 43, 44, 45, 46`; report mean and standard deviation.
- Report accuracy, precision, recall, F1, AUROC, AUPRC, TP/TN/FP/FN,
  false-trust, false-removal, training time, inference latency, and parameter
  count where applicable.
- Keep ROAD IDS metrics separate from CAV reliability and AGS-PBFT grouping
  metrics (selection rates, stability, reassignment frequency, false
  inclusion/exclusion, consensus success, and grouping latency).

No accuracy target is a training objective. A reported result is valid only
for the locked dataset and configuration recorded with it.
