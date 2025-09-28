"""Heuristic travelling salesman solver with multi-modal support."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from math import inf
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .shortest_path import Edge, PathResult, WeightStrategy, shortest_path


@dataclass(frozen=True)
class TourLeg:
    """Single leg of the computed tour."""

    start: str
    end: str
    path: PathResult


@dataclass(frozen=True)
class TourResult:
    """Aggregate outcome of a tour computation."""

    route: List[str]
    legs: List[TourLeg]
    total_distance: float
    total_time: float


class TourComputationError(RuntimeError):
    """Raised when a feasible tour cannot be constructed."""


def compute_tour(
    edges: Iterable[Edge],
    start: str,
    targets: Sequence[str],
    *,
    allowed_modes: Optional[Sequence[str] | str] = None,
    strategy: WeightStrategy | str = WeightStrategy.TIME,
    max_iterations: int = 50,
) -> TourResult:
    """Compute a round-trip visiting each target using a nearest-neighbour + 2-opt heuristic."""

    if not targets:
        return TourResult(route=[start, start], legs=[], total_distance=0.0, total_time=0.0)

    strategy = WeightStrategy(strategy)
    nodes = [start] + list(dict.fromkeys(targets))  # ensure determinism and remove duplicates
    pair_paths = _precompute_pair_paths(edges, nodes, allowed_modes, strategy)

    initial_route = _nearest_neighbour_route(start, targets, pair_paths, strategy)
    optimised_route = _two_opt(initial_route, pair_paths, strategy, max_iterations)

    legs: List[TourLeg] = []
    total_distance = 0.0
    total_time = 0.0
    for origin, destination in zip(optimised_route, optimised_route[1:]):
        path = pair_paths[(origin, destination)]
        legs.append(TourLeg(start=origin, end=destination, path=path))
        total_distance += path.total_distance
        total_time += path.total_time

    return TourResult(
        route=optimised_route,
        legs=legs,
        total_distance=total_distance,
        total_time=total_time,
    )


PairKey = Tuple[str, str]
PairMap = Dict[PairKey, PathResult]


def _precompute_pair_paths(
    edges: Iterable[Edge],
    nodes: Sequence[str],
    allowed_modes: Optional[Sequence[str] | str],
    strategy: WeightStrategy,
) -> PairMap:
    pair_paths: PairMap = {}
    edge_list = list(edges)
    for origin in nodes:
        for destination in nodes:
            if origin == destination:
                continue
            key = (origin, destination)
            if key in pair_paths:
                continue
            try:
                pair_paths[key] = shortest_path(
                    edge_list,
                    start=origin,
                    goal=destination,
                    allowed_modes=allowed_modes,
                    strategy=strategy,
                )
            except ValueError as exc:  # propagate with extra context
                raise TourComputationError(
                    f"No feasible path between {origin!r} and {destination!r}: {exc}"
                ) from exc
    return pair_paths


def _nearest_neighbour_route(
    start: str,
    targets: Sequence[str],
    pair_paths: PairMap,
    strategy: WeightStrategy,
) -> List[str]:
    remaining = list(dict.fromkeys(targets))
    route: List[str] = [start]
    current = start
    while remaining:
        next_node = min(
            remaining,
            key=lambda node: _path_cost(pair_paths[(current, node)], strategy),
        )
        route.append(next_node)
        remaining.remove(next_node)
        current = next_node
    route.append(start)
    return route


def _two_opt(
    route: List[str],
    pair_paths: PairMap,
    strategy: WeightStrategy,
    max_iterations: int,
) -> List[str]:
    if len(route) <= 3:
        return route

    best_route = route
    best_cost = _route_cost(best_route, pair_paths, strategy)
    iteration = 0
    improved = True

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, len(best_route) - 2):
            for j in range(i + 1, len(best_route) - 1):
                if j - i == 1:
                    continue  # skip adjacent edges
                candidate = best_route[:i] + best_route[i:j][::-1] + best_route[j:]
                cost = _route_cost(candidate, pair_paths, strategy)
                if cost + 1e-9 < best_cost:
                    best_route = candidate
                    best_cost = cost
                    improved = True
                    break
            if improved:
                break
    return best_route


def _route_cost(route: List[str], pair_paths: PairMap, strategy: WeightStrategy) -> float:
    total = 0.0
    for origin, destination in zip(route, route[1:]):
        path = pair_paths.get((origin, destination))
        if path is None:
            return inf
        total += _path_cost(path, strategy)
    return total


def _path_cost(path: PathResult, strategy: WeightStrategy) -> float:
    return path.total_distance if strategy is WeightStrategy.DISTANCE else path.total_time
