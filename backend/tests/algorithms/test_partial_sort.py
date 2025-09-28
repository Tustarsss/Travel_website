"""Unit tests for the partial sorting utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import pytest

from app.algorithms import PartialSorter, RankedItem, top_k, top_k_with_scores


def test_top_k_basic() -> None:
    items = [5, 1, 9, 3, 7]
    result = top_k(items, 3)
    assert result == [9, 7, 5]


def test_top_k_respects_key() -> None:
    words = ["alpha", "beta", "kappa", "gama"]
    result = top_k(words, 2, key=len)
    assert result == ["kappa", "alpha"]


def test_top_k_handles_zero_or_empty() -> None:
    assert top_k([], 5) == []
    assert top_k([1, 2, 3], 0) == []


def test_partial_sorter_incremental() -> None:
    sorter: PartialSorter[int] = PartialSorter(4)
    sorter.extend(range(10))
    assert sorter.top() == [9, 8, 7, 6]

    sorter.push(42)
    assert sorter.top() == [42, 9, 8, 7]


def test_top_k_with_scores_returns_ranked_items() -> None:
    values = [1, 4, 2, 8]
    ranked: List[RankedItem[int]] = top_k_with_scores(values, 2)
    assert [item.value for item in ranked] == [8, 4]
    assert [item.score for item in ranked] == [8.0, 4.0]


@dataclass
class Destination:
    name: str
    popularity: int
    rating: float


def test_partial_sorter_combined_score() -> None:
    destinations = [
        Destination("Scenic A", popularity=90, rating=4.8),
        Destination("Scenic B", popularity=80, rating=4.9),
        Destination("Scenic C", popularity=95, rating=4.2),
        Destination("Scenic D", popularity=70, rating=4.5),
    ]

    def score(item: Destination) -> float:
        return 0.6 * item.popularity + 0.4 * item.rating * 20

    top = PartialSorter.top_k(destinations, 2, key=score)
    assert [dest.name for dest in top] == ["Scenic A", "Scenic C"]


def test_partial_sorter_invalid_k() -> None:
    with pytest.raises(ValueError):
        PartialSorter(-1)


def test_partial_sorter_float_precision() -> None:
    # Use values that would cause rounding issues if not handled as floats
    values = [math.pi, math.e, math.tau]
    ranked = PartialSorter.top_k_with_scores(values, 2)
    assert ranked[0].score == pytest.approx(math.tau)
    assert ranked[1].score == pytest.approx(math.pi)