"""Lightweight inverted index with TF-IDF ranking."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class Posting:
    doc_id: str
    term_frequency: int


class InvertedIndex:
    """In-memory inverted index supporting insertion, removal, and TF-IDF search."""

    def __init__(self) -> None:
        self._postings: Dict[str, List[Posting]] = defaultdict(list)
        self._doc_lengths: Dict[str, int] = {}
        self._doc_terms: Dict[str, Counter[str]] = {}
        self._total_docs = 0

    def add(self, doc_id: str, tokens: Sequence[str]) -> None:
        if doc_id in self._doc_terms:
            self.remove(doc_id)
        term_counts = Counter(_normalise_token(token) for token in tokens if token)
        if not term_counts:
            self._doc_lengths[doc_id] = 0
            self._doc_terms[doc_id] = Counter()
            self._total_docs += 1
            return

        for term, frequency in term_counts.items():
            self._postings[term].append(Posting(doc_id, frequency))
        self._doc_terms[doc_id] = term_counts
        self._doc_lengths[doc_id] = sum(term_counts.values())
        self._total_docs += 1

    def remove(self, doc_id: str) -> None:
        if doc_id not in self._doc_terms:
            raise KeyError(f"Document {doc_id!r} not indexed")

        term_counts = self._doc_terms.pop(doc_id)
        self._doc_lengths.pop(doc_id, None)
        for term in list(term_counts.keys()):
            postings = self._postings.get(term, [])
            self._postings[term] = [posting for posting in postings if posting.doc_id != doc_id]
            if not self._postings[term]:
                del self._postings[term]
        self._total_docs = max(self._total_docs - 1, 0)

    def search(self, tokens: Iterable[str], top_k: int = 10) -> List[tuple[str, float]]:
        query_terms = [
            _normalise_token(token) for token in tokens if token
        ]
        if not query_terms:
            return []

        scores: Dict[str, float] = defaultdict(float)
        for term in query_terms:
            postings = self._postings.get(term)
            if not postings:
                continue
            idf = math.log((1 + self._total_docs) / (1 + len(postings))) + 1
            for posting in postings:
                tf = posting.term_frequency / self._doc_lengths.get(posting.doc_id, 1)
                scores[posting.doc_id] += tf * idf

        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]

    def documents(self) -> int:
        return self._total_docs

    def vocabulary(self) -> int:
        return len(self._postings)


def _normalise_token(token: str) -> str:
    return token.lower()
