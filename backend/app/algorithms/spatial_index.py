"""R-tree spatial index with range query, insertion, and deletion support."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box used by the spatial index."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        if self.min_x > self.max_x or self.min_y > self.max_y:
            raise ValueError("BoundingBox min values must not exceed max values")

    @classmethod
    def from_point(cls, x: float, y: float) -> "BoundingBox":
        return cls(x, y, x, y)

    def area(self) -> float:
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    def perimeter(self) -> float:
        return 2 * ((self.max_x - self.min_x) + (self.max_y - self.min_y))

    def union(self, other: "BoundingBox") -> "BoundingBox":
        return BoundingBox(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y),
        )

    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            other.min_x > self.max_x
            or other.max_x < self.min_x
            or other.min_y > self.max_y
            or other.max_y < self.min_y
        )

    def contains_point(self, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def enlargement(self, other: "BoundingBox") -> float:
        return self.union(other).area() - self.area()


@dataclass
class LeafEntry(Generic[T]):
    bbox: BoundingBox
    payload: T


@dataclass
class BranchEntry(Generic[T]):
    bbox: BoundingBox
    child: "RTreeNode[T]"


class RTreeNode(Generic[T]):
    __slots__ = ("is_leaf", "entries", "parent")

    def __init__(self, is_leaf: bool) -> None:
        self.is_leaf = is_leaf
        self.entries: List[LeafEntry[T] | BranchEntry[T]] = []
        self.parent: Optional["RTreeNode[T]"] = None

    def compute_bbox(self) -> BoundingBox:
        if not self.entries:
            raise ValueError("Cannot compute bounding box of an empty node")
        bbox = _entry_bbox(self.entries[0])
        for entry in self.entries[1:]:
            bbox = bbox.union(_entry_bbox(entry))
        return bbox


class RTree(Generic[T]):
    """Simple R-tree implementation with quadratic split heuristic."""

    def __init__(self, max_entries: int = 8, min_entries: Optional[int] = None) -> None:
        if max_entries < 4:
            raise ValueError("max_entries must be at least 4 for meaningful splits")
        self.max_entries = max_entries
        self.min_entries = min_entries or max_entries // 2
        if self.min_entries < 2:
            raise ValueError("min_entries must be at least 2")
        self.root: RTreeNode[T] = RTreeNode(is_leaf=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def insert(self, bbox: BoundingBox, payload: T) -> None:
        leaf = self._choose_leaf(bbox)
        leaf.entries.append(LeafEntry(bbox, payload))
        node = leaf
        while True:
            if len(node.entries) <= self.max_entries:
                self._refresh_parent_bbox(node)
                if node.parent is None:
                    break
                node = node.parent
                continue

            node, new_node = self._split_node(node)
            if node.parent is None:
                new_root = RTreeNode[T](is_leaf=False)
                node.parent = new_root
                new_node.parent = new_root
                new_root.entries = [
                    BranchEntry(node.compute_bbox(), node),
                    BranchEntry(new_node.compute_bbox(), new_node),
                ]
                self.root = new_root
                break

            parent = node.parent
            self._update_parent_entry(parent, node)
            parent.entries.append(BranchEntry(new_node.compute_bbox(), new_node))
            new_node.parent = parent
            node = parent

    def delete(self, bbox: BoundingBox, payload: T) -> None:
        leaf = self._find_leaf(self.root, bbox, payload)
        if leaf is None:
            raise KeyError("Entry not found in R-tree")

        removed = False
        for idx, entry in enumerate(leaf.entries):
            if isinstance(entry, LeafEntry) and entry.payload == payload and entry.bbox == bbox:
                leaf.entries.pop(idx)
                removed = True
                break
        if not removed:
            raise KeyError("Entry not found in R-tree")

        reinserts: List[LeafEntry[T]] = []
        node: Optional[RTreeNode[T]] = leaf
        while node is not None:
            if node is not self.root and len(node.entries) < self.min_entries:
                parent = node.parent
                if parent is None:
                    break
                self._remove_child(parent, node)
                if node.is_leaf:
                    reinserts.extend(entry for entry in node.entries if isinstance(entry, LeafEntry))
                else:
                    reinserts.extend(self._collect_leaf_entries(node))
                node = parent
                continue

            self._refresh_parent_bbox(node)
            node = node.parent

        if not self.root.is_leaf and len(self.root.entries) == 1:
            child = self.root.entries[0]
            assert isinstance(child, BranchEntry)
            self.root = child.child
            self.root.parent = None
        elif self.root.is_leaf and not self.root.entries:
            self.root = RTreeNode(is_leaf=True)

        for entry in reinserts:
            self.insert(entry.bbox, entry.payload)

    def range_search(self, bbox: BoundingBox) -> List[T]:
        results: List[T] = []
        self._range_search_node(self.root, bbox, results)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _choose_leaf(self, bbox: BoundingBox) -> RTreeNode[T]:
        node = self.root
        while not node.is_leaf:
            assert all(isinstance(entry, BranchEntry) for entry in node.entries)
            node = min(
                (entry for entry in node.entries if isinstance(entry, BranchEntry)),
                key=lambda entry: (
                    entry.bbox.enlargement(bbox),
                    entry.bbox.area(),
                ),
            ).child
        return node

    def _split_node(self, node: RTreeNode[T]) -> Tuple[RTreeNode[T], RTreeNode[T]]:
        group1, group2 = self._quadratic_split(node.entries)
        node.entries = group1
        new_node = RTreeNode[T](is_leaf=node.is_leaf)
        new_node.entries = group2

        if not node.is_leaf:
            for entry in node.entries:
                assert isinstance(entry, BranchEntry)
                entry.child.parent = node
            for entry in new_node.entries:
                assert isinstance(entry, BranchEntry)
                entry.child.parent = new_node

        return node, new_node

    def _quadratic_split(
        self, entries: Sequence[LeafEntry[T] | BranchEntry[T]]
    ) -> Tuple[List[LeafEntry[T] | BranchEntry[T]], List[LeafEntry[T] | BranchEntry[T]]]:
        items = list(entries)
        if len(items) <= 2:
            return [items[0]], [items[1]]

        seed1_index = seed2_index = -1
        max_d = -inf
        for i in range(len(items) - 1):
            bbox_i = _entry_bbox(items[i])
            for j in range(i + 1, len(items)):
                bbox_j = _entry_bbox(items[j])
                d = bbox_i.union(bbox_j).area() - bbox_i.area() - bbox_j.area()
                if d > max_d:
                    max_d = d
                    seed1_index, seed2_index = i, j

        group1 = [items.pop(seed1_index)]
        group2 = [items.pop(seed2_index - 1 if seed2_index > seed1_index else seed2_index)]
        bbox1 = _entry_bbox(group1[0])
        bbox2 = _entry_bbox(group2[0])

        while items:
            if len(group1) + len(items) == self.min_entries:
                group1.extend(items)
                break
            if len(group2) + len(items) == self.min_entries:
                group2.extend(items)
                break

            entry = items.pop(0)
            bbox = _entry_bbox(entry)
            enlargement1 = bbox1.enlargement(bbox)
            enlargement2 = bbox2.enlargement(bbox)

            if enlargement1 < enlargement2 or (
                enlargement1 == enlargement2 and bbox1.area() < bbox2.area()
            ):
                group1.append(entry)
                bbox1 = bbox1.union(bbox)
            else:
                group2.append(entry)
                bbox2 = bbox2.union(bbox)

        return group1, group2

    def _refresh_parent_bbox(self, node: RTreeNode[T]) -> None:
        parent = node.parent
        if parent is None:
            return
        for entry in parent.entries:
            if isinstance(entry, BranchEntry) and entry.child is node:
                entry.bbox = node.compute_bbox()
                break

    def _update_parent_entry(self, parent: RTreeNode[T], child: RTreeNode[T]) -> None:
        for entry in parent.entries:
            if isinstance(entry, BranchEntry) and entry.child is child:
                entry.bbox = child.compute_bbox()
                return
        parent.entries.append(BranchEntry(child.compute_bbox(), child))

    def _remove_child(self, parent: RTreeNode[T], child: RTreeNode[T]) -> None:
        for idx, entry in enumerate(parent.entries):
            if isinstance(entry, BranchEntry) and entry.child is child:
                parent.entries.pop(idx)
                return

    def _collect_leaf_entries(self, node: RTreeNode[T]) -> List[LeafEntry[T]]:
        if node.is_leaf:
            return [entry for entry in node.entries if isinstance(entry, LeafEntry)]
        collected: List[LeafEntry[T]] = []
        for entry in node.entries:
            assert isinstance(entry, BranchEntry)
            collected.extend(self._collect_leaf_entries(entry.child))
        return collected

    def _find_leaf(
        self, node: RTreeNode[T], bbox: BoundingBox, payload: T
    ) -> Optional[RTreeNode[T]]:
        if node.is_leaf:
            for entry in node.entries:
                if isinstance(entry, LeafEntry) and entry.bbox == bbox and entry.payload == payload:
                    return node
            return None

        for entry in node.entries:
            assert isinstance(entry, BranchEntry)
            if entry.bbox.intersects(bbox):
                result = self._find_leaf(entry.child, bbox, payload)
                if result is not None:
                    return result
        return None

    def _range_search_node(
        self, node: RTreeNode[T], bbox: BoundingBox, results: List[T]
    ) -> None:
        if node.is_leaf:
            for entry in node.entries:
                if isinstance(entry, LeafEntry) and entry.bbox.intersects(bbox):
                    results.append(entry.payload)
            return

        for entry in node.entries:
            assert isinstance(entry, BranchEntry)
            if entry.bbox.intersects(bbox):
                self._range_search_node(entry.child, bbox, results)


def _entry_bbox(entry: LeafEntry[T] | BranchEntry[T]) -> BoundingBox:
    return entry.bbox
