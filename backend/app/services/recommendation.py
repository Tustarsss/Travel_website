"""Recommendation-related service utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Iterable, Sequence

from app.algorithms import InvertedIndex, PartialSorter
from app.models.locations import Region, RegionType
from app.repositories import RegionRepository

_TOKEN_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)


class RecommendationSort(str, Enum):
    """Supported ranking strategies for region recommendations."""

    HYBRID = "hybrid"
    POPULARITY = "popularity"
    RATING = "rating"


@dataclass(slots=True)
class RegionRecommendation:
    """Region enriched with recommendation metadata."""

    region: Region
    score: float
    interest_matches: list[str]
    base_score: float


@dataclass(slots=True)
class RecommendationResult:
    """Structured response for recommendation queries."""

    items: list[RegionRecommendation]
    sort_by: RecommendationSort
    generated_at: datetime
    total_candidates: int


class RecommendationService:
    """Service orchestrating region recommendations."""

    def __init__(self, region_repository: RegionRepository) -> None:
        self._region_repository = region_repository

    async def recommend_regions(
        self,
        *,
        limit: int = 10,
        sort_by: RecommendationSort = RecommendationSort.HYBRID,
        interests: Sequence[str] | None = None,
        search: str | None = None,
        region_type: RegionType | None = None,
        interests_only: bool = False,
    ) -> RecommendationResult:
        """Return the top regions according to the configured strategy."""

        if limit <= 0:
            return RecommendationResult(
                items=[],
                sort_by=sort_by,
                generated_at=datetime.now(timezone.utc),
                total_candidates=0,
            )

        regions = await self._region_repository.list_regions(region_type=region_type)
        filtered = self._filter_by_search(regions, search)

        candidates: list[RegionRecommendation] = []
        interest_terms = self._normalise_terms(interests or [])

        for region in filtered:
            matches = self._match_interests(region, interest_terms)
            if interests_only and interest_terms and not matches:
                continue

            base_score = self._score_region(region, sort_by)
            interest_boost = self._interest_boost(len(matches), sort_by)
            final_score = base_score + interest_boost

            candidates.append(
                RegionRecommendation(
                    region=region,
                    score=final_score,
                    interest_matches=matches,
                    base_score=base_score,
                )
            )

        ranked = PartialSorter.top_k(candidates, k=limit, key=lambda item: item.score)

        return RecommendationResult(
            items=ranked,
            sort_by=sort_by,
            generated_at=datetime.now(timezone.utc),
            total_candidates=len(candidates),
        )

    def _filter_by_search(self, regions: Sequence[Region], search: str | None) -> list[Region]:
        if not search:
            return list(regions)

        index = InvertedIndex()
        id_to_region: dict[str, Region] = {}
        for region in regions:
            if region.id is None:
                continue
            doc_id = str(region.id)
            index.add(doc_id, self._tokenise_region(region))
            id_to_region[doc_id] = region

        if index.documents() == 0:
            return list(regions)

        hits = index.search(self._tokenise_query(search), top_k=index.documents())
        if not hits:
            return []

        kept_ids = {doc_id for doc_id, _ in hits}
        return [region for region in regions if region.id is not None and str(region.id) in kept_ids]

    def _match_interests(self, region: Region, interests: Sequence[str]) -> list[str]:
        if not interests:
            return []

        region_terms = set(self._tokenise_region(region))
        matches = [interest for interest in interests if interest in region_terms]
        return matches

    def _score_region(self, region: Region, sort_by: RecommendationSort) -> float:
        popularity = float(region.popularity or 0)
        rating = float(region.rating or 0)

        if sort_by is RecommendationSort.POPULARITY:
            return popularity
        if sort_by is RecommendationSort.RATING:
            return rating
        return 0.6 * popularity + 0.4 * rating

    def _interest_boost(self, match_count: int, sort_by: RecommendationSort) -> float:
        if match_count == 0:
            return 0.0
        weight = 15.0 if sort_by is not RecommendationSort.RATING else 4.0
        return match_count * weight

    def _tokenise_region(self, region: Region) -> list[str]:
        tokens: list[str] = []
        tokens.extend(self._tokenise_text(region.name))
        if region.city:
            tokens.extend(self._tokenise_text(region.city))
        if region.description:
            tokens.extend(self._tokenise_text(region.description))
        return tokens

    def _tokenise_text(self, text: str) -> list[str]:
        return [token.lower() for token in _TOKEN_PATTERN.findall(text)]

    def _tokenise_query(self, query: str) -> list[str]:
        return self._tokenise_text(query)

    def _normalise_terms(self, terms: Iterable[str]) -> list[str]:
        return [term.lower() for term in terms if term]
