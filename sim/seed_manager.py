from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedSplit:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]


def split_seeds(seeds: list[int], train_fraction: float = 0.6, validation_fraction: float = 0.2) -> SeedSplit:
    if len(set(seeds)) != len(seeds) or len(seeds) < 5: raise ValueError("supply at least five unique seeds")
    ordered, train_end = tuple(sorted(seeds)), int(len(seeds) * train_fraction)
    validation_end = train_end + int(len(seeds) * validation_fraction)
    return SeedSplit(ordered[:train_end], ordered[train_end:validation_end], ordered[validation_end:])
