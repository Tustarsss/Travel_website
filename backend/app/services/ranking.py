"""Ranking helpers for the service layer."""

from __future__ import annotations

from typing import Callable, Iterable, Sequence, TypeVar

from app.algorithms import PartialSorter

T = TypeVar("T")


def top_k_by_score(items: Iterable[T], k: int, score: Callable[[T], float]) -> Sequence[T]:
	"""Return the ``k`` highest scoring items.

	This keeps service code thin: controllers just pass data and a scoring
	function, while the heavy lifting stays in the algorithm layer.
	"""

	return PartialSorter.top_k(items, k=k, key=score)
