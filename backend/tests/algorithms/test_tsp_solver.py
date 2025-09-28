from __future__ import annotations

import pytest

from app.algorithms import (
    Edge,
    TourComputationError,
    WeightStrategy,
    compute_tour,
)


BASIC_EDGES = [
    Edge("A", "B", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("B", "A", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("B", "C", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("C", "B", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("C", "D", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("D", "C", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("D", "A", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("A", "D", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("A", "C", distance=3.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("C", "A", distance=3.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("B", "D", distance=3.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
    Edge("D", "B", distance=3.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
]


def test_compute_tour_returns_cycle_covering_all_targets() -> None:
    result = compute_tour(BASIC_EDGES, start="A", targets=["B", "C", "D"], allowed_modes=("walk",))

    assert result.route[0] == "A" and result.route[-1] == "A"
    assert set(result.route[1:-1]) == {"B", "C", "D"}
    assert len(result.legs) == 4
    assert result.total_distance == pytest.approx(4.0)
    assert result.total_time == pytest.approx(4.0)


MODES_EDGES = [
    Edge("A", "B", distance=100.0, ideal_speed=5.0, congestion=1.0, transport_modes=("bike",)),
    Edge("B", "A", distance=100.0, ideal_speed=5.0, congestion=1.0, transport_modes=("bike",)),
    Edge("B", "C", distance=200.0, ideal_speed=10.0, congestion=0.5, transport_modes=("bike", "electric_cart")),
    Edge("C", "B", distance=200.0, ideal_speed=10.0, congestion=0.5, transport_modes=("bike", "electric_cart")),
    Edge("C", "A", distance=100.0, ideal_speed=3.0, congestion=0.5, transport_modes=("electric_cart",)),
    Edge("A", "C", distance=100.0, ideal_speed=3.0, congestion=0.5, transport_modes=("electric_cart",)),
]


def test_compute_tour_respects_allowed_modes_and_time_strategy() -> None:
    result = compute_tour(
        MODES_EDGES,
        start="A",
        targets=["B", "C"],
        allowed_modes=("bike", "electric_cart"),
        strategy=WeightStrategy.TIME,
    )

    assert result.route == ["A", "B", "C", "A"]
    assert result.total_time == pytest.approx(120.0)
    # Last leg should combine multiple edges under the hood (C -> B -> A)
    final_leg = result.legs[-1]
    assert [segment.target for segment in final_leg.path.segments] == ["B", "A"]


def test_compute_tour_raises_when_unreachable() -> None:
    with pytest.raises(TourComputationError):
        compute_tour(
            [
                Edge("A", "B", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
                Edge("B", "A", distance=1.0, ideal_speed=1.0, congestion=1.0, transport_modes=("walk",)),
            ],
            start="A",
            targets=["C"],
        )
