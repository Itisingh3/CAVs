# Crypto-Agile, ML-Predictive AGS-PBFT for Quantum-Resilient CAV Communication

This repository is the reproducible reference implementation accompanying the planned networking letter. It implements a frozen protocol specification, a faithful AGS-PBFT baseline, a lightweight ML-adaptive variant, a deterministic CPU-first experiment harness, statistical analysis, and a ProVerif model.

## Status and scope

- Default suite: ML-KEM-768 plus ML-DSA-65 through Open Quantum Safe (`liboqs-python`).
- Saber is deliberately not enabled: it is an experimental backend and must be added only through a maintained PQClean/liboqs binding.
- The bundled development harness is not a SUMO/Veins/OMNeT++ simulation and is not reported as a networking experiment.
- The reliability implementation separates an ML probability from learned historical, consensus, and network evidence. The coefficients are fitted on validation data, never hand-selected. Cryptographic failures remain authoritative and cannot be overridden by ML.
- The selected public source is ROAD, a real-vehicle CAN intrusion dataset. It trains only the automotive intrusion-probability branch; it is not represented as V2X or PBFT data. See `data/README.md`.

## Temporal-model experiment

The four existing lightweight predictors remain available for the online
grouping path. LSTM, GRU and BiLSTM are separate optional offline models:
they are trained on genuine causal tensors of shape
`[samples, sequence_length, 10]`, not renamed single rows. Each tensor ends at
the decision time `t`; it never includes observations after `t`, and does not
cross scenario/node or split boundaries. The experimental question is:

> Does temporal modelling improve reliability-aware dynamic grouping compared
> with non-temporal models?

Install the optional deep-learning stack and use the CPU smoke configuration
before a full GPU/Colab run:

```powershell
pip install -r requirements-deep.txt
python -m ml.train data/derived/cav_reliability_windows.csv --model lstm --epochs 5 --sequence-length 10 --batch-size 32 --output results/lstm_smoke.csv
python -m ml.train data/derived/cav_reliability_windows.csv --model bilstm --epochs 50 --sequence-length 20 --batch-size 64 --device cuda --output results/bilstm.csv --evaluate-locked-test
```

Defaults live in `configs/ml_training.yaml` (50 epochs, 20 windows, batch size
64, learning rate 0.001, patience 8, seed 42). Command-line arguments override
them. BiLSTM is an offline comparison model; all deployment decisions still use
only observations available through `t`.

## Hardware-aware setup

The implementation uses CPU-only, dependency-free predictors. Logistic regression, a shallow decision tree, a small random forest, and a single-hidden-layer MLP are compared offline; only the selected model's bounded inference runs on the grouping decision path. Your Ryzen 5 5600H, 8 GB RAM, and GTX 1650 are sufficient for the reference runs; no GPU framework is used. Keep parallel experiment workers at 1-2 while using the full simulator.

Create an isolated environment and install the maintained PQC binding (the library requires a compatible `liboqs` installation):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

For the workspace-local dependency installation used during development, also set:

```powershell
$env:PYTHONPATH = "$PWD\.vendor"
```

If `oqs` cannot be imported, protocol cryptography is intentionally unavailable. The non-cryptographic consensus, simulation, analysis, and specification checks remain usable.

## Commands

```powershell
# Run standard-library tests (PQC integration tests skip until oqs is installed)
python -m unittest discover -s tests -v

# Optional: download the documented external automotive CAN source.
# It is a substantial archive, is excluded from git, and must not be called CAV/PBFT data.
python -m data.download_road --destination data/raw/ROAD

# Compare all four predictors using only pre-registered train/validation rows.
# The CSV must contain split,reliable and the six columns from spec/ml_grouping_interface.md.
python -m ml.evaluate_predictors results/reliability_train_validation.csv --output results/ml_predictor_comparison.csv

# Full causal reliability training, after collecting instrumented protocol windows
# in the schema documented at data/README.md.  The locked test split is read only
# when the explicit flag is supplied.
python -m ml.train_temporal_pipeline data/derived/cav_reliability_windows.csv --output results/temporal_validation.csv
python -m ml.train_temporal_pipeline data/derived/cav_reliability_windows.csv --output results/temporal_final.csv --evaluate-locked-test
```

## Reproducibility rules

1. Freeze `spec/` before running evaluations. Any protocol change requires a spec version bump and a ProVerif-model update.
2. Split seeds with `sim.seed_manager` before model tuning. Final claims may use only the `test` split.
3. Preserve each run's JSONL event log and manifest. Figures/tables must be generated from these files, never hand-entered.
4. Use only a completely locked trace group for final metrics. Development-harness values and external CAN results are not networking-performance claims.

See `spec/` for protocol details and `CAV_Letter_Outline.md` for the paper architecture.
