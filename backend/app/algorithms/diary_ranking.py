"""Diary ranking and recommendation algorithms."""

import heapq
import math
from typing import Callable, List, Optional

from app.models.diaries import Diary


class DiaryRankingAlgorithm:
    """Algorithms for diary ranking and recommendations."""

    def top_k_by_score(
        self,
        candidates: List[Diary],
        k: int,
        score_func: Callable[[Diary], float],
    ) -> List[Diary]:
        """
        Find top K diaries using heap-based selection.
        
        Time complexity: O(n log k) where n is the number of candidates
        Space complexity: O(k)
        
        Args:
            candidates: List of diary candidates
            k: Number of top results to return
            score_func: Function to calculate score for each diary
            
        Returns:
            List of top K diaries sorted by score (descending)
        """
        if not candidates:
            return []
            
        if len(candidates) <= k:
            return sorted(candidates, key=score_func, reverse=True)
        
        # Use heapq.nlargest for efficient top-k selection
        return heapq.nlargest(k, candidates, key=score_func)

    def hybrid_score(
        self, 
        diary: Diary, 
        interests: Optional[List[str]] = None,
        weights: Optional[dict] = None
    ) -> float:
        """
        Calculate hybrid recommendation score.
        
        Default formula:
        score = 0.4 * popularity_score + 0.4 * rating_score + 0.2 * interest_score
        
        Args:
            diary: Diary to score
            interests: User interest tags
            weights: Custom weight dict with keys: 'popularity', 'rating', 'interest'
            
        Returns:
            Normalized score between 0.0 and 1.0
        """
        # Default weights
        if weights is None:
            weights = {
                'popularity': 0.4,
                'rating': 0.4,
                'interest': 0.2,
            }
        
        # Popularity score (log-normalized to prevent popular diaries from dominating)
        # Assumes max popularity ~10000
        popularity_score = math.log(diary.popularity + 1) / math.log(10001)
        popularity_score = min(popularity_score, 1.0)
        
        # Rating score (normalized to 0-1)
        rating_score = diary.rating / 5.0 if diary.ratings_count > 0 else 0.0
        
        # Apply penalty for low rating count (avoid bias from single high ratings)
        if diary.ratings_count < 5:
            rating_score *= (diary.ratings_count / 5.0)
        
        # Interest matching score
        interest_score = 0.0
        if interests and diary.tags:
            matched_tags = set(diary.tags) & set(interests)
            interest_score = len(matched_tags) / len(interests) if interests else 0.0
            interest_score = min(interest_score, 1.0)
        
        # Calculate weighted sum
        final_score = (
            weights['popularity'] * popularity_score +
            weights['rating'] * rating_score +
            weights['interest'] * interest_score
        )
        
        return final_score

    def popularity_score(self, diary: Diary) -> float:
        """Pure popularity-based scoring."""
        return float(diary.popularity)

    def rating_score(self, diary: Diary) -> float:
        """Pure rating-based scoring with count weighting."""
        if diary.ratings_count == 0:
            return 0.0
        
        # Weighted rating considering sample size
        # Wilson score or Bayesian average can be used for more sophisticated approach
        base_score = diary.rating * diary.ratings_count
        
        # Apply logarithmic scaling to ratings count
        count_factor = math.log(diary.ratings_count + 1)
        
        return base_score * count_factor

    def recency_score(self, diary: Diary) -> float:
        """Time-based scoring for "latest" sort."""
        # Return timestamp for sorting
        # Can be converted to days since epoch for normalization
        return diary.created_at.timestamp() if diary.created_at else 0.0


# Singleton instance
ranking_algorithm = DiaryRankingAlgorithm()
