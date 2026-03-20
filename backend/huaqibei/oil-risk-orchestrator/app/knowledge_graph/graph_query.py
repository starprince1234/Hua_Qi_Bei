from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from collections import deque

_GRAPH_PATH = Path(__file__).parent / "graph_data.json"


@lru_cache(maxsize=1)
def _load_graph() -> dict:
    return json.loads(_GRAPH_PATH.read_text(encoding="utf-8"))


def _adjacency(directed: bool = True) -> dict[str, list[str]]:
    graph = _load_graph()
    adj: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    for edge in graph["edges"]:
        adj[edge["source"]].append(edge["target"])
        if not directed:
            adj[edge["target"]].append(edge["source"])
    return adj


def get_transmission_path(source: str, target: str) -> list[str]:
    """BFS to find the shortest directed path from *source* to *target*."""
    adj = _adjacency()
    if source not in adj or target not in adj:
        return []

    queue: deque[list[str]] = deque([[source]])
    visited = {source}

    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == target:
            return path
        for neighbour in adj.get(node, []):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])
    return []


def get_affected_industries(factor: str) -> list[str]:
    """Return industry nodes reachable from *factor*."""
    graph = _load_graph()
    industry_ids = {n["id"] for n in graph["nodes"] if n.get("type") == "industry"}
    adj = _adjacency()

    visited: set[str] = set()
    queue: deque[str] = deque([factor])
    affected: list[str] = []

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node in industry_ids and node != factor:
            affected.append(node)
        for neighbour in adj.get(node, []):
            if neighbour not in visited:
                queue.append(neighbour)
    return affected


def get_related_factors(industry: str) -> list[str]:
    """Return macro/financial nodes that can reach *industry* (reverse BFS)."""
    graph = _load_graph()
    macro_types = {"macro", "financial", "organization"}
    macro_ids = {n["id"] for n in graph["nodes"] if n.get("type") in macro_types}

    # Build reverse adjacency
    rev: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    for edge in graph["edges"]:
        rev[edge["target"]].append(edge["source"])

    visited: set[str] = set()
    queue: deque[str] = deque([industry])
    factors: list[str] = []

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node in macro_ids and node != industry:
            factors.append(node)
        for neighbour in rev.get(node, []):
            if neighbour not in visited:
                queue.append(neighbour)
    return factors
