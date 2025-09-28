"""Shortest path utilities using Dijkstra's algorithm."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from heapq import heappop, heappush
from itertools import count
from math import inf
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


class WeightStrategy(str, Enum):
    """Supported weighting strategies for shortest path queries."""

    DISTANCE = "distance"
    TIME = "time"


@dataclass(frozen=True)
class Edge:
    """Directed edge in the transport graph."""

    source: str
    target: str
    distance: float
    ideal_speed: float
    congestion: float
    transport_modes: Tuple[str, ...] = ("walk",)

    def __post_init__(self) -> None:
        modes = tuple(mode.lower() for mode in self.transport_modes if mode)
        if not modes:
            raise ValueError("transport_modes must contain at least one mode")
        if self.distance < 0:
            raise ValueError("distance must be non-negative")
        if self.ideal_speed <= 0:
            raise ValueError("ideal_speed must be positive")
        if self.congestion <= 0:
            raise ValueError("congestion must be positive")
        object.__setattr__(self, "transport_modes", modes)

    @property
    def travel_time(self) -> float:
        """Actual travel time along the edge considering congestion."""

        return self.distance / (self.ideal_speed * self.congestion)


@dataclass(frozen=True)
class PathSegment:
    """Single hop within a computed route."""

    source: str
    target: str
    transport_mode: str
    distance: float
    time: float


@dataclass(frozen=True)
class PathResult:
    """Aggregate result of a shortest path computation."""

    nodes: List[str]
    segments: List[PathSegment]
    total_distance: float
    total_time: float


def shortest_path(
    edges: Iterable[Edge],
    start: str,
    goal: str,
    *,
    allowed_modes: Optional[Sequence[str] | str] = None,
    strategy: WeightStrategy | str = WeightStrategy.TIME,
) -> PathResult:
    """Compute the optimal route between two nodes using Dijkstra's algorithm."""

    if start == goal:
        return PathResult(nodes=[start], segments=[], total_distance=0.0, total_time=0.0)

    strategy = WeightStrategy(strategy)
    allowed = _normalise_modes(allowed_modes)
    adjacency: Dict[str, List[Edge]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source, []).append(edge)

    queue: List[Tuple[float, int, str]] = []
    order = count()
    heappush(queue, (0.0, next(order), start))

    best_cost: Dict[str, float] = {start: 0.0}
    best_distance: Dict[str, float] = {start: 0.0}
    best_time: Dict[str, float] = {start: 0.0}
    previous: Dict[str, Tuple[str, Edge, str]] = {}
    visited: set[str] = set()

    while queue:
        cost, _, node = heappop(queue)
        if node in visited:
            continue
        visited.add(node)

        if node == goal:
            break

        for edge in adjacency.get(node, []):
            mode = _select_mode(edge, allowed)
            if mode is None:
                continue

            segment_distance = edge.distance
            segment_time = edge.travel_time
            if segment_distance < 0 or segment_time < 0:
                raise ValueError("negative edge weight detected")

            new_distance = best_distance[node] + segment_distance
            new_time = best_time[node] + segment_time
            new_cost = new_distance if strategy is WeightStrategy.DISTANCE else new_time

            if new_cost < best_cost.get(edge.target, inf):
                best_cost[edge.target] = new_cost
                best_distance[edge.target] = new_distance
                best_time[edge.target] = new_time
                previous[edge.target] = (node, edge, mode)
                heappush(queue, (new_cost, next(order), edge.target))

    if goal not in best_cost:
        raise ValueError(f"No path found from {start!r} to {goal!r}")

    nodes: List[str] = []
    segments: List[PathSegment] = []
    cursor = goal
    while cursor != start:
        if cursor not in previous:
            raise ValueError(f"No path found from {start!r} to {goal!r}")
        prev_node, edge, mode = previous[cursor]
        nodes.append(cursor)
        segments.append(
            PathSegment(
                source=prev_node,
                target=cursor,
                transport_mode=mode,
                distance=edge.distance,
                time=edge.travel_time,
            )
        )
        cursor = prev_node
    nodes.append(start)
    nodes.reverse()
    segments.reverse()

    return PathResult(
        nodes=nodes,
        segments=segments,
        total_distance=best_distance[goal],
        total_time=best_time[goal],
    )


def _normalise_modes(modes: Optional[Sequence[str] | str]) -> Optional[Tuple[str, ...]]:
    if modes is None:
        return None
    if isinstance(modes, str):
        iterable: Sequence[str] = [modes]
    else:
        iterable = modes
    normalised = tuple(sorted({mode.lower() for mode in iterable if mode}))
    return normalised or None


def _select_mode(edge: Edge, allowed: Optional[Tuple[str, ...]]) -> Optional[str]:
    if allowed is None:
        return edge.transport_modes[0]
    allowed_set = set(allowed)
    for mode in edge.transport_modes:
        if mode in allowed_set:
            return mode
    return None
