"""Repository and cache seams for intelligence persistence adapters."""

from .protocols import (
    BacktestRepository,
    CacheProvider,
    EventRepository,
    FactorRepository,
)

__all__ = [
    "BacktestRepository",
    "CacheProvider",
    "EventRepository",
    "FactorRepository",
]
