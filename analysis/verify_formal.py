"""Run frozen ProVerif models and emit auditable CSV/JSON verification tables."""
from __future__ import annotations
import argparse
import csv
import json
import subprocess
from pathlib import Path

MODELS = {"final_ake": "formal/model.pv", "composed_protocol": "formal/composed_protocol.pv", "kem_kdf_secrecy_equivalence": "formal/secrecy_equivalence.pv"}

def verify(proverif: Path, output: Path) -> list[dict[str, str]]:
    output.mkdir(parents=True, exist_ok=True); rows = []
    for name, source in MODELS.items():
        result = subprocess.run([str(proverif), source], text=True, capture_output=True, check=False)
        text = result.stdout + result.stderr
        (output / f"{name}.txt").write_text(text, encoding="utf-8")
        outcomes = [line.strip() for line in text.splitlines() if line.startswith("RESULT ")]
        scope = "credential/AKE authentication, replay, and suite binding" if name == "final_ake" else ("credential/AKE/vote correspondence" if name == "composed_protocol" else "isolated KEM/KDF equivalence; not a complete AKE secrecy proof")
        rows.append({"model": name, "source": source, "exit_code": str(result.returncode), "result_count": str(len(outcomes)), "all_queries_true": str(bool(outcomes) and all(" is true." in line for line in outcomes)).lower(), "scope": scope})
    with (output / "verification_table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (output / "verification_table.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--proverif", type=Path, default=Path(r"C:\Tools\proverif2.05\proverif.exe")); parser.add_argument("--output", type=Path, default=Path("reports/formal")); args = parser.parse_args()
    for row in verify(args.proverif, args.output): print(row)
if __name__ == "__main__": main()
