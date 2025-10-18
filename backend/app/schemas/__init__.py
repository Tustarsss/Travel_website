"""Schema definitions for external communication."""

from .recommendation import RegionRecommendationItem, RegionRecommendationResponse, RegionSummary
from .routing import RouteNode, RoutePlanResponse, RouteSegment
from .facility import FacilityRouteItem, FacilityRouteResponse
from .search import (
	RegionNodeSearchResponse,
	RegionNodeSummary,
	RegionSearchResponse,
	RegionSearchResult,
)
from .diary import (
	DiaryCreateRequest,
	DiaryUpdateRequest,
	DiaryListItem,
	DiaryDetail,
	DiaryCreateResponse,
	DiaryRatingRequest,
	DiaryRatingResponse,
	DiaryRatingItem,
	DiaryRatingListResponse,
	DiaryViewRequest,
	DiaryRecommendationItem,
	DiaryRecommendationResponse,
	DiarySearchResult,
	DiarySearchResponse,
	AnimationGenerateRequest,
	DiaryAnimationResponse,
	DiaryListParams,
	UserSummary as DiaryUserSummary,
	RegionSummary as DiaryRegionSummary,
)
from .user import UserPublic, UserCreateRequest, UserUpdateRequest

__all__ = [
	"RegionRecommendationItem",
	"RegionRecommendationResponse",
	"RegionSummary",
	"FacilityRouteItem",
	"FacilityRouteResponse",
	"RoutePlanResponse",
	"RouteNode",
	"RouteSegment",
	"RegionSearchResult",
	"RegionSearchResponse",
	"RegionNodeSummary",
	"RegionNodeSearchResponse",
	# Diary schemas
	"DiaryCreateRequest",
	"DiaryUpdateRequest",
	"DiaryListItem",
	"DiaryDetail",
	"DiaryCreateResponse",
	"DiaryRatingRequest",
	"DiaryRatingResponse",
	"DiaryRatingItem",
	"DiaryRatingListResponse",
	"DiaryViewRequest",
	"DiaryRecommendationItem",
	"DiaryRecommendationResponse",
	"DiarySearchResult",
	"DiarySearchResponse",
	"AnimationGenerateRequest",
	"DiaryAnimationResponse",
	"DiaryListParams",
	"DiaryUserSummary",
	"DiaryRegionSummary",
	"UserPublic",
	"UserCreateRequest",
	"UserUpdateRequest",
]
