from __future__ import annotations

import pytest

from app.algorithms import InvertedIndex


@pytest.fixture
def index() -> InvertedIndex:
    idx = InvertedIndex()
    idx.add("doc1", ["Scenic", "Lake", "Beautiful"])
    idx.add("doc2", ["Historic", "Temple", "Lake"])
    idx.add("doc3", ["Modern", "Museum"])
    return idx


def test_search_returns_ranked_results(index: InvertedIndex) -> None:
    results = index.search(["lake"])
    assert [doc_id for doc_id, _ in results] == ["doc1", "doc2"]

    results = index.search(["lake", "historic"])
    assert results[0][0] == "doc2"


def test_remove_document_updates_index(index: InvertedIndex) -> None:
    index.remove("doc2")
    assert index.documents() == 2
    assert "doc2" not in dict(index.search(["lake"]))

    with pytest.raises(KeyError):
        index.remove("doc2")


def test_add_overwrites_existing_document(index: InvertedIndex) -> None:
    index.add("doc1", ["New", "Content"])
    results = dict(index.search(["scenic"]))
    assert "doc1" not in results
    assert index.vocabulary() >= 4


def test_search_ignores_empty_queries(index: InvertedIndex) -> None:
    assert index.search([]) == []
    assert index.search([" "]) == []
