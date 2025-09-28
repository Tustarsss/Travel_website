"""Algorithm implementations used across the backend."""

from .compression import compress_text, decompress_text
from .inverted_index import InvertedIndex, Posting
from .partial_sort import PartialSorter, RankedItem, top_k, top_k_with_scores
from .shortest_path import Edge, PathResult, PathSegment, WeightStrategy, shortest_path
from .spatial_index import BoundingBox, RTree
from .tsp import TourComputationError, TourLeg, TourResult, compute_tour

__all__ = [
	"PartialSorter",
	"RankedItem",
	"top_k",
	"top_k_with_scores",
	"Edge",
	"PathSegment",
	"PathResult",
	"WeightStrategy",
	"shortest_path",
	"BoundingBox",
	"RTree",
	"InvertedIndex",
	"Posting",
	"compress_text",
	"decompress_text",
	"TourLeg",
	"TourResult",
	"TourComputationError",
	"compute_tour",
]
