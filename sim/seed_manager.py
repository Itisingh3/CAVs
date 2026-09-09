from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path


@dataclass(frozen=True)
class SeedSplit:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]


STREAM_OFFSETS = {
    "mobility": 10_000,
    "channel": 20_000,
    "mac": 30_000,
    "traffic": 40_000,
    "attack": 50_000,
    "ml": 60_000,
}


def derive_streams(base_seed: int) -> dict[str, int]:
    """Return deterministic, non-overlapping seeds for each stochastic subsystem."""
    if base_seed < 0: raise ValueError("base_seed must be non-negative")
    return {name: base_seed + offset for name, offset in STREAM_OFFSETS.items()}


def write_manifest(path: Path, split: SeedSplit) -> Path:
    """Write all seed allocations before an experiment is executed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "base_seed", *STREAM_OFFSETS])
        writer.writeheader()
        for split_name in ("train", "validation", "test"):
            for base_seed in getattr(split, split_name):
                writer.writerow({"split": split_name, "base_seed": base_seed, **derive_streams(base_seed)})
    return path


def split_seeds(seeds: list[int], train_fraction: float = 0.6, validation_fraction: float = 0.2) -> SeedSplit:
    if len(set(seeds)) != len(seeds) or len(seeds) < 5: raise ValueError("supply at least five unique seeds")
    ordered, train_end = tuple(sorted(seeds)), int(len(seeds) * train_fraction)
    validation_end = train_end + int(len(seeds) * validation_fraction)
    return SeedSplit(ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:])
