"""Merge per-model locked-test CSVs into auditable CSV and Markdown tables."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path

FIELDS = ("model", "accuracy", "precision", "recall", "f1", "auroc", "auprc", "true_positive", "true_negative", "false_positive", "false_negative", "false_trust_rate", "false_removal_rate")

def build(inputs: list[Path], output: Path) -> list[dict[str, str]]:
    rows = []
    for path in inputs:
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(row for row in csv.DictReader(handle) if row["stage"] == "locked_test")
    for row in rows:
        fp, fn, tn, tp = (int(row["false_positive"]), int(row["false_negative"]), int(row["true_negative"]), int(row["true_positive"]))
        row["false_trust_rate"] = str(fp / (fp + tn) if fp + tn else 0.0)
        row["false_removal_rate"] = str(fn / (fn + tp) if fn + tp else 0.0)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows([{field: row.get(field, "") for field in FIELDS} for row in rows])
    markdown = ["| " + " | ".join(FIELDS) + " |", "|" + "|".join(["---"] * len(FIELDS)) + "|"]
    markdown.extend("| " + " | ".join(row.get(field, "") for field in FIELDS) + " |" for row in rows)
    output.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return rows

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("inputs", type=Path, nargs="+"); parser.add_argument("--output", type=Path, default=Path("reports/model_comparison.csv")); args = parser.parse_args()
    print(f"models={len(build(args.inputs, args.output))}\nreport={args.output}")
if __name__ == "__main__": main()
