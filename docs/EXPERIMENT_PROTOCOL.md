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

`python -m analysis.stats <paired-event-dir> --output <report-dir>` produces
per-run 95% confidence intervals, paired t-test p-values (when SciPy is
available), and paired Cohen's *d* effect sizes. Development-harness reports
carry their non-network warning and are not letter evidence.

Use `python -m analysis.run_ml_multiseed data/derived/cav_reliability_windows.csv`
to execute the prescribed five seeds and produce a locked-test mean/std table.
The default includes all seven candidates; pass only the four lightweight
models locally if PyTorch is unavailable, then run the recurrent candidates in
Colab. The online grouping deployment remains a latency-bounded lightweight
predictor even when LSTM/GRU/BiLSTM win the offline comparison.
