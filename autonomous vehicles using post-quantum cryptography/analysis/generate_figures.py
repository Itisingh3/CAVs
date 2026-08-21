"""Deliberately data-only until a paper figure style is agreed; never embeds result values."""
from pathlib import Path


def require_summary(summary_csv: Path) -> Path:
    if not summary_csv.is_file(): raise FileNotFoundError("generate figures only from an analysis summary CSV")
    return summary_csv
