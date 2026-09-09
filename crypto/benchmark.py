"""Actual-machine PQC microbenchmark. Writes measured values; it never uses literature figures."""
from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path

from crypto.mlkem_backend import MLKEM768Backend
from crypto.mldsa_backend import MLDSA65Backend
from crypto.suite_interface import CryptoUnavailable


def _measure(operation, repeats: int) -> tuple[float, object]:
    values, value = [], None
    for _ in range(repeats):
        start = time.perf_counter_ns(); value = operation(); values.append((time.perf_counter_ns() - start) / 1_000_000)
    return statistics.fmean(values), value


def run(output: Path, repeats: int = 100) -> Path:
    kem, signer = MLKEM768Backend(), MLDSA65Backend()
    keygen_kem_ms, kem_keys = _measure(kem.keygen, repeats); kem_pk, kem_sk = kem_keys
    encap_ms, encap = _measure(lambda: kem.encapsulate(kem_pk), repeats); ciphertext, _ = encap
    decap_ms, _ = _measure(lambda: kem.decapsulate(kem_sk, ciphertext), repeats)
    keygen_sig_ms, sig_keys = _measure(signer.keygen, repeats); sig_pk, sig_sk = sig_keys
    message = b"CAV PQC benchmark v1"; sign_ms, signature = _measure(lambda: signer.sign(sig_sk, message), repeats)
    verify_ms, verified = _measure(lambda: signer.verify(sig_pk, message, signature), repeats)
    if not verified: raise CryptoUnavailable("benchmark signature verification failed")
    rows = [
        {"algorithm":"ML-KEM-768","operation":"keygen","mean_ms":keygen_kem_ms,"bytes":f"pk={len(kem_pk)};sk={len(kem_sk)}"},
        {"algorithm":"ML-KEM-768","operation":"encap","mean_ms":encap_ms,"bytes":f"ct={len(ciphertext)}"},
        {"algorithm":"ML-KEM-768","operation":"decap","mean_ms":decap_ms,"bytes":"ss=32"},
        {"algorithm":"ML-DSA-65","operation":"keygen","mean_ms":keygen_sig_ms,"bytes":f"pk={len(sig_pk)};sk={len(sig_sk)}"},
        {"algorithm":"ML-DSA-65","operation":"sign","mean_ms":sign_ms,"bytes":f"sig={len(signature)}"},
        {"algorithm":"ML-DSA-65","operation":"verify","mean_ms":verify_ms,"bytes":""},
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args(); print(run(args.output, args.repeats))


if __name__ == "__main__": main()
