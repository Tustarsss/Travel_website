from __future__ import annotations

import random

import pytest

from app.algorithms import BoundingBox, RTree


def box_for_point(x: float, y: float) -> BoundingBox:
    padding = 0.01
    return BoundingBox(x - padding, y - padding, x + padding, y + padding)


def test_range_search_returns_expected_payloads() -> None:
    index: RTree[int] = RTree(max_entries=4)
    points = {
        1: (0.0, 0.0),
        2: (5.0, 5.0),
        3: (10.0, 10.0),
        4: (15.0, 15.0),
    }

    for pid, (x, y) in points.items():
        index.insert(box_for_point(x, y), pid)

    results = index.range_search(BoundingBox(4.0, 4.0, 12.0, 12.0))
    assert set(results) == {2, 3}


def test_deletion_removes_entry_and_structure_recovers() -> None:
    index: RTree[int] = RTree(max_entries=4)
    boxes = [box_for_point(float(i), float(i)) for i in range(8)]

    for i, bbox in enumerate(boxes):
        index.insert(bbox, i)

    index.delete(boxes[2], 2)
    remaining = index.range_search(BoundingBox(-1.0, -1.0, 20.0, 20.0))
    assert set(remaining) == set(range(8)) - {2}

    with pytest.raises(KeyError):
        index.delete(boxes[2], 2)

    index.insert(boxes[2], 2)
    restored = index.range_search(BoundingBox(-1.0, -1.0, 20.0, 20.0))
    assert set(restored) == set(range(8))


def test_node_split_creates_internal_nodes() -> None:
    random.seed(42)
    index: RTree[int] = RTree(max_entries=4)
    for i in range(9):
        index.insert(box_for_point(random.uniform(0, 100), random.uniform(0, 100)), i)

    assert not index.root.is_leaf
    all_payloads = index.range_search(BoundingBox(-100.0, -100.0, 200.0, 200.0))
    assert set(all_payloads) == set(range(9))


def test_range_search_with_rectangular_boxes() -> None:
    index: RTree[str] = RTree(max_entries=4)
    rects = {
        "north": BoundingBox(0.0, 5.0, 10.0, 10.0),
        "south": BoundingBox(0.0, -10.0, 10.0, -5.0),
        "center": BoundingBox(2.0, 2.0, 8.0, 8.0),
        "west": BoundingBox(-10.0, 0.0, -5.0, 10.0),
    }
    for label, bbox in rects.items():
        index.insert(bbox, label)

    overlapping = index.range_search(BoundingBox(1.0, 1.0, 9.0, 9.0))
    assert set(overlapping) == {"north", "center"}

    disjoint = index.range_search(BoundingBox(-4.0, -4.0, -1.0, -1.0))
    assert disjoint == []
