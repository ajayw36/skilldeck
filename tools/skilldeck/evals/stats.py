"""Honest statistics for small, noisy pairwise samples: a two-sided sign test.
Anything fancier is false precision on top of judge noise."""

from __future__ import annotations

import math


def sign_test(wins: int, losses: int) -> float:
    """Two-sided sign test p-value; ties are excluded before calling this."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarize(wins: int, losses: int, ties: int) -> str:
    p = sign_test(wins, losses)
    return f"{wins}W / {losses}L / {ties}T (sign test p={p:.3f})"
