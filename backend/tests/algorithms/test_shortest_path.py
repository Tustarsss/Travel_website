from __future__ import annotations

import math

import pytest

from app.algorithms.shortest_path import Edge, PathResult, WeightStrategy, shortest_path


EDGES = [
    Edge("A", "B", distance=100.0, ideal_speed=1.4, congestion=1.0, transport_modes=("walk", "bike")),
    Edge("B", "C", distance=120.0, ideal_speed=1.4, congestion=1.0, transport_modes=("walk",)),
    Edge("C", "D", distance=80.0, ideal_speed=1.4, congestion=1.0, transport_modes=("walk", "electric_cart")),
    Edge("B", "D", distance=200.0, ideal_speed=4.0, congestion=0.5, transport_modes=("bike", "electric_cart")),
    Edge("A", "D", distance=500.0, ideal_speed=1.4, congestion=1.0, transport_modes=("walk",)),
]


def test_shortest_path_by_distance_prefers_shorter_route() -> None:
    result: PathResult = shortest_path(
        EDGES,
        start="A",
        goal="D",
        allowed_modes=("walk",),
        strategy=WeightStrategy.DISTANCE,
    )

    assert result.nodes == ["A", "B", "C", "D"]
    assert result.total_distance == pytest.approx(300.0)
    assert result.total_time == pytest.approx(sum(segment.time for segment in result.segments))


def test_shortest_path_by_time_prefers_faster_modes() -> None:
    result = shortest_path(
        EDGES,
        start="A",
        goal="D",
        allowed_modes=("bike", "electric_cart"),
        strategy=WeightStrategy.TIME,
    )

    assert result.nodes == ["A", "B", "D"]
    assert result.total_distance == pytest.approx(300.0)
    expected_time = (100.0 / 1.4) + (200.0 / (4.0 * 0.5))
    assert result.total_time == pytest.approx(expected_time)


def test_shortest_path_returns_zero_route_when_start_equals_goal() -> None:
    result = shortest_path(EDGES, start="A", goal="A")
    assert result.nodes == ["A"]
    assert result.total_distance == 0.0
    assert result.total_time == 0.0
    assert not result.segments


def test_shortest_path_raises_when_no_transport_mode_available() -> None:
    with pytest.raises(ValueError):
        shortest_path(
            EDGES,
            start="A",
            goal="D",
            allowed_modes=("electric_cart",),
        )


def test_negative_edge_weight_is_rejected() -> None:
    with pytest.raises(ValueError):
        Edge("X", "Y", distance=-10.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",))

    with pytest.raises(ValueError):
        Edge("X", "Y", distance=10.0, ideal_speed=-1.0, congestion=1.0, transport_modes=("walk",))

    with pytest.raises(ValueError):
        Edge("X", "Y", distance=10.0, ideal_speed=1.0, congestion=0.0, transport_modes=("walk",))
