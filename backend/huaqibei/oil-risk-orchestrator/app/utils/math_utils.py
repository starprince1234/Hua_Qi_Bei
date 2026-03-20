from __future__ import annotations

import math


def compute_var(returns: list[float], confidence: float = 0.95) -> float:
    """
    Compute the Historical Value-at-Risk (VaR) at a given confidence level.

    Args:
        returns: List of return observations.
        confidence: Confidence level (e.g. 0.95 for 95 % VaR).

    Returns:
        VaR as a negative number (loss).
    """
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    index = int((1 - confidence) * len(sorted_returns))
    return sorted_returns[max(index, 0)]


def compute_cvar(returns: list[float], confidence: float = 0.95) -> float:
    """
    Compute the Conditional Value-at-Risk (CVaR / Expected Shortfall).

    Args:
        returns: List of return observations.
        confidence: Confidence level.

    Returns:
        CVaR as a negative number (expected loss beyond VaR).
    """
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    cutoff_index = int((1 - confidence) * len(sorted_returns))
    tail = sorted_returns[: max(cutoff_index, 1)]
    return sum(tail) / len(tail)


def normalize(arr: list[float]) -> list[float]:
    """Min-max normalise a list to [0, 1]."""
    if not arr:
        return []
    lo, hi = min(arr), max(arr)
    span = hi - lo
    if span == 0:
        return [0.0] * len(arr)
    return [(x - lo) / span for x in arr]


def safe_divide(a: float, b: float, fallback: float = 0.0) -> float:
    """Divide *a* by *b*, returning *fallback* when *b* is (near) zero."""
    if abs(b) < 1e-12:
        return fallback
    return a / b
