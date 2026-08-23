# Crypto-Agile, ML-Predictive AGS-PBFT for Quantum-Resilient CAV Communication

This repository is the reproducible reference implementation accompanying the planned networking letter. It implements a frozen protocol specification, a faithful AGS-PBFT baseline, a lightweight ML-adaptive variant, a deterministic CPU-first experiment harness, statistical analysis, and a ProVerif model.

## Status and scope

- Default suite: ML-KEM-768 plus ML-DSA-65 through Open Quantum Safe (`liboqs-python`).
- Saber is deliberately not enabled: it is an experimental backend and must be added only through a maintained PQClean/liboqs binding.
- The bundled simulator is a **documented lightweight equivalent**, designed for development and reproducibility on an 8 GB RAM laptop. It is not a replacement for the final SUMO/Veins/OMNeT++ study.
- No experiment result is supplied or claimed by this repository. Results are generated from logged runs only.

## Hardware-aware setup

The implementation uses CPU-only online logistic regression and the Python standard library. Your Ryzen 5 5600H, 8 GB RAM, and GTX 1650 are sufficient for the reference runs; no GPU or deep-learning framework is used. Keep parallel experiment workers at 1-2 while using the full simulator.

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

# Run the controlled paired development model (30 seeds, 300 rounds, 60 warm-up)
# This validates the experimental pipeline only; it is not a SUMO/Veins result.
python -m sim.run_paired_development_experiment --density 60 --seeds 30 --rounds 300 --warmup-rounds 60 --output results/development_paired

# Aggregate at the run/seed level and write paired-effect statistics
python -m analysis.stats results/development_paired --output results/analysis_paired
```

## Reproducibility rules

1. Freeze `spec/` before running evaluations. Any protocol change requires a spec version bump and a ProVerif-model update.
2. Split seeds with `sim.seed_manager` before model tuning. Final claims may use only the `test` split.
3. Preserve each run's JSONL event log and manifest. Figures/tables must be generated from these files, never hand-entered.
4. Use at least 30 paired test seeds for paper figures. Development-model runs are pipeline validation only; repeat the same protocol through SUMO/Veins/OMNeT++ before making a networking-performance claim.

See `spec/` for protocol details and `CAV_Letter_Outline.md` for the paper architecture.
