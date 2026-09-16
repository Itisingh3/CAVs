# Colab / GPU run

Install the optional deep stack, clone the repository, and place ROAD at the
same path expected by the commands. Device selection defaults to `auto` and
uses CUDA only when available.

```bash
pip install -r requirements-deep.txt
python -m data.preprocess_road --root data/raw/ROAD --output data/derived/road_can_windows.csv
python -m ml.train data/derived/cav_reliability_windows.csv --model gru --epochs 50 --sequence-length 20 --batch-size 64 --device cuda --output reports/gru_validation.csv
```

For a CPU smoke test use `--epochs 5 --sequence-length 10 --batch-size 32`.
The CAV telemetry CSV must already contain preassigned scenario/node-level
splits; the ROAD output is not a substitute for it.

The ready-to-run notebook is [train_models_colab.ipynb](../notebooks/train_models_colab.ipynb). It installs only the optional deep dependency, reports the selected device, creates the two separated datasets, and runs all seven candidates.
