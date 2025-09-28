"""Efficient partial sorting helpers for recommendation workloads."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappush, heappushpop
from itertools import count
from typing import Callable, Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RankedItem(Generic[T]):
    """Value enriched with its ranking score."""

    value: T
    score: float


class PartialSorter(Generic[T]):
    """Maintain the top-k items using a fixed-size min-heap.

    The implementation targets recommendation scenarios where only a small subset of
    the highest-scoring entries is required and recomputing a full sort would be wasteful.
    """

    def __init__(self, k: int, *, key: Optional[Callable[[T], float]] = None) -> None:
        if k < 0:
            raise ValueError("k must be non-negative")
        self._k = k
        self._key = key or (lambda item: float(item))
        self._counter = count()
        self._heap: List[Tuple[float, str, int, T]] = []

    def push(self, item: T) -> None:
        """Consider a new item for inclusion in the top-k set."""

        if self._k == 0:
            return
        score = float(self._key(item))
        order = next(self._counter)
        entry = (score, repr(item), -order, item)
        if len(self._heap) < self._k:
            heappush(self._heap, entry)
        else:
            heappushpop(self._heap, entry)

    def extend(self, items: Iterable[T]) -> None:
        """Consume a batch of items."""

        for item in items:
            self.push(item)

    def top(self) -> List[T]:
        """Return the current top-k items sorted by descending score."""

        return [item for _, _, _, item in sorted(self._heap, reverse=True)]

    def top_ranked(self) -> List[RankedItem[T]]:
        """Return ranked items with their scores."""

        return [RankedItem(value=item, score=score) for score, _, _, item in sorted(self._heap, reverse=True)]

    @classmethod
    def top_k(
        cls,
        items: Iterable[T],
        k: int,
        *,
        key: Optional[Callable[[T], float]] = None,
    ) -> List[T]:
        """Convenience helper that processes an iterable in a single call."""

        sorter: PartialSorter[T] = cls(k, key=key)
        sorter.extend(items)
        return sorter.top()

    @classmethod
    def top_k_with_scores(
        cls,
        items: Iterable[T],
        k: int,
        *,
        key: Optional[Callable[[T], float]] = None,
    ) -> List[RankedItem[T]]:
        """Return both values and scores for inspection/logging purposes."""

        sorter: PartialSorter[T] = cls(k, key=key)
        sorter.extend(items)
        return sorter.top_ranked()


def top_k(
    items: Sequence[T] | Iterable[T],
    k: int,
    *,
    key: Optional[Callable[[T], float]] = None,
) -> List[T]:
    """Functional-style wrapper around :class:`PartialSorter`.

    The helper accepts any iterable and returns the highest ``k`` items by the provided
    score function. When ``k`` is zero or the input is empty, an empty list is returned.
    """

    if k <= 0:
        return []
    return PartialSorter.top_k(items, k, key=key)


def top_k_with_scores(
    items: Sequence[T] | Iterable[T],
    k: int,
    *,
    key: Optional[Callable[[T], float]] = None,
) -> List[RankedItem[T]]:
    """Functional helper that also returns the ranking score for each item."""

    if k <= 0:
        return []
    return PartialSorter.top_k_with_scores(items, k, key=key)
