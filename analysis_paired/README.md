# Controlled Development-Model Results - Not for Letter Section VI

This folder contains a **30-paired-seed, 300-round controlled development-model experiment** at density 60. It validates that the implementation has a causal path from policy -> membership -> consensus outcome -> logged metrics, and that the ML model exits fallback after warm-up.

It is **not** a SUMO/Veins/OMNeT++ experiment and must not be presented as vehicular-network performance evidence in the networking letter. The latent reliability/congestion process in `sim/run_experiment.py` is a controlled test environment, not a calibrated wireless/mobility model.

`summary.csv` contains one post-warm-up mean per seed and variant. `paired_comparison.csv` uses the same 30 seeds for baseline and ML and reports run-level paired differences, 95% confidence intervals, Cohen's dz, and the paired t statistic. It does not use individual rounds as independent samples.

The next research step is to preserve this exact pairing, warm-up, event schema, and run-level analysis when replacing the development model with the SUMO/Veins/OMNeT++ adapter.
