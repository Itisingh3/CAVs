"""Measured-primitive, closed-form PBFT overhead projection.

This is algebra over local microbenchmarks, not a network simulator.  It reports
signature-only control bytes and CPU cryptographic work for one PBFT round.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import statistics
import time
from pathlib import Path


def sha3_mean_ms(repetitions: int = 50_000) -> float:
    sample = b"CAV-CONSENSUS-v1" + bytes(256)
    timings = []
    for _ in range(repetitions):
        start = time.perf_counter_ns(); hashlib.sha3_256(sample).digest()
        timings.append(time.perf_counter_ns() - start)
    return statistics.fmean(timings) / 1_000_000


def read_pqc(path: Path) -> dict[str, float]:
    values = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle): values[(row["algorithm"], row["operation"])] = float(row["mean_ms"])
    return values


def generate(benchmark_csv: Path, output_dir: Path, figure: Path) -> tuple[Path, Path]:
    pqc, hash_ms = read_pqc(benchmark_csv), sha3_mean_ms()
    sign_ms, verify_ms, signature_bytes = pqc[("ML-DSA-65", "sign")], pqc[("ML-DSA-65", "verify")], 3309
    rows = []
    for n in (4, 10, 20, 50, 100):
        transmissions = 2 * (n * n - 1)  # PRE-PREPARE + PREPARE + COMMIT + REPLY broadcasts
        sign_ops, verify_ops = 2 * n + 1, transmissions
        rows.append({
            "replicas": n, "signed_transmissions": transmissions,
            "signature_only_control_bytes": transmissions * signature_bytes,
            "mldsa_sign_operations": sign_ops, "mldsa_verify_operations": verify_ops,
            "mldsa_projected_crypto_ms": sign_ops * sign_ms + verify_ops * verify_ms,
            "sha3_proxy_operations": transmissions,
            "sha3_proxy_compute_ms": transmissions * hash_ms,
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path, meta_path = output_dir / "closed_form_overhead_projection.csv", output_dir / "closed_form_overhead_metadata.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with meta_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"]); writer.writeheader()
        writer.writerows([
            {"metric":"ML-DSA-65 sign mean (ms)", "value":sign_ms}, {"metric":"ML-DSA-65 verify mean (ms)", "value":verify_ms},
            {"metric":"ML-DSA-65 signature bytes", "value":signature_bytes}, {"metric":"SHA3-256 proxy mean (ms)", "value":hash_ms},
            {"metric":"formula", "value":"M(n)=2(n^2-1); S(n)=2n+1; V(n)=M(n)"},
            {"metric":"scope", "value":"One PBFT round; signature-only payload bytes; no PHY/MAC/queueing/network latency."},
        ])
    import matplotlib.pyplot as plt
    xs = [r["replicas"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.35), constrained_layout=True)
    axes[0].plot(xs, [r["signature_only_control_bytes"] / 1024 for r in rows], marker="o", color="#1F5A99", linewidth=2)
    axes[0].set(title="(a) Signed control payload projection", xlabel="PBFT replicas (n)", ylabel="Signature-only control bytes (KiB/round)")
    axes[1].plot(xs, [r["mldsa_projected_crypto_ms"] for r in rows], marker="s", color="#D97904", linewidth=2, label="ML-DSA-65 signing + verification")
    axes[1].plot(xs, [r["sha3_proxy_compute_ms"] for r in rows], marker="o", linestyle="--", color="#526D82", linewidth=1.7, label="Unkeyed SHA3-256 proxy")
    axes[1].set(title="(b) CPU cryptographic-work projection", xlabel="PBFT replicas (n)", ylabel="Measured primitive work (ms/round)")
    axes[1].legend(frameon=False, fontsize=7.2)
    for axis in axes:
        axis.grid(alpha=.22); axis.spines[["top", "right"]].set_visible(False); axis.set_xticks(xs)
    fig.text(.5, -.035, "Closed-form projection using local ML-DSA-65 microbenchmarks. SHA3 is an unkeyed, non-authenticating computational proxy only—not a signature baseline or network-latency result.", ha="center", fontsize=7.6, color="#526D82")
    figure.parent.mkdir(parents=True, exist_ok=True)
    svg, png = figure.with_suffix(".svg"), figure.with_suffix(".png")
    fig.savefig(svg, bbox_inches="tight"); fig.savefig(png, dpi=240, bbox_inches="tight"); plt.close(fig)
    return csv_path, meta_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--benchmarks", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--figure", type=Path, required=True)
    arguments = parser.parse_args(); print(*generate(arguments.benchmarks, arguments.output, arguments.figure), sep="\n")
