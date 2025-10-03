import apiClient from './apiClient'
import type {
  FacilityCategory,
  FacilityRouteResponse,
  MapFeatureCollection,
  RecommendationSort,
  RegionNodeSearchResponse,
  RegionNodeSummary,
  RegionRecommendationResponse,
  RegionSearchResponse,
  RegionSearchResult,
  RegionType,
  RoutePlanResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'

export interface RecommendationQuery {
  limit?: number
  sortBy?: RecommendationSort
  interests?: string[]
  interestsOnly?: boolean
  search?: string
  regionType?: RegionType | ''
}

export const fetchRegionRecommendations = async (
  params: RecommendationQuery = {}
): Promise<RegionRecommendationResponse> => {
  const queryParams = {
    limit: params.limit,
    sort_by: params.sortBy,
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    interests_only: params.interestsOnly,
    q: params.search || undefined,
    region_type: params.regionType || undefined,
  }

  const { data } = await apiClient.get<RegionRecommendationResponse>('/recommendations/regions', {
    params: queryParams,
  })

  return data
}

export interface RegionSearchQuery {
  keyword: string
  limit?: number
}

export const searchRegions = async (
  params: RegionSearchQuery
): Promise<RegionSearchResult[]> => {
  const queryParams = {
    q: params.keyword,
    limit: params.limit ?? 10,
  }

  const { data } = await apiClient.get<RegionSearchResponse>('/regions/search', {
    params: queryParams,
  })

  return data.items
}

export const fetchRegionDetail = async (regionId: number): Promise<RegionSearchResult> => {
  const { data } = await apiClient.get<RegionSearchResult>(`/regions/${regionId}`)
  return data
}

export interface RegionNodeSearchQuery {
  regionId: number
  keyword: string
  limit?: number
}

export const searchRegionNodes = async (
  params: RegionNodeSearchQuery
): Promise<RegionNodeSummary[]> => {
  const { regionId, keyword, limit } = params
  const { data } = await apiClient.get<RegionNodeSearchResponse>(
    `/regions/${regionId}/nodes/search`,
    {
      params: {
        q: keyword,
        limit: limit ?? 10,
      },
    }
  )

  return data.items
}

export const fetchRegionNodeDetail = async (
  regionId: number,
  nodeId: number
): Promise<RegionNodeSummary> => {
  const { data } = await apiClient.get<RegionNodeSummary>(
    `/regions/${regionId}/nodes/${nodeId}`
  )
  return data
}

export interface RoutePlanQuery {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes?: TransportMode[]
}

export const fetchRoutePlan = async (params: RoutePlanQuery): Promise<RoutePlanResponse> => {
  const queryParams = {
    region_id: params.regionId,
    start_node_id: params.startNodeId,
    end_node_id: params.endNodeId,
    strategy: params.strategy,
    transport_modes: params.transportModes && params.transportModes.length > 0 ? params.transportModes : undefined,
  }

  const { data } = await apiClient.get<RoutePlanResponse>('/routing/routes', {
    params: queryParams,
  })

  return data
}

export interface FacilityQuery {
  regionId: number
  originNodeId: number
  radiusMeters?: number | null
  limit?: number
  strategy: WeightStrategy
  categories?: FacilityCategory[]
  transportModes?: TransportMode[]
}

export const fetchNearbyFacilities = async (
  params: FacilityQuery
): Promise<FacilityRouteResponse> => {
  const queryParams = {
    region_id: params.regionId,
    origin_node_id: params.originNodeId,
    radius_meters: params.radiusMeters ?? undefined,
    limit: params.limit,
    strategy: params.strategy,
    category:
      params.categories && params.categories.length > 0
        ? params.categories
        : undefined,
    transport_modes:
      params.transportModes && params.transportModes.length > 0
        ? params.transportModes
        : undefined,
  }

  const { data } = await apiClient.get<FacilityRouteResponse>('/facilities/nearby', {
    params: queryParams,
  })

  return data
}

export const fetchRegionMapData = async (
  regionId: number,
  includeRoads: boolean = false
): Promise<MapFeatureCollection> => {
  const { data } = await apiClient.get<MapFeatureCollection>(`/map-data/${regionId}`, {
    params: {
      include_roads: includeRoads,
    },
  })
  return data
}

// ===== Diary API Functions =====

import type {
  DiarySortBy,
  DiaryListResponse,
  DiaryRecommendationParams,
  DiaryRecommendationResponse,
  DiaryCreateRequest,
  DiaryCreateResponse,
  DiaryUpdateRequest,
  DiaryDetail,
  DiaryRatingRequest,
  DiaryRatingResponse,
  AnimationGenerateRequest,
  DiaryAnimation,
} from '../types/diary'

/**
 * Get personalized diary recommendations
 */
export const fetchDiaryRecommendations = async (
  params: DiaryRecommendationParams = {}
): Promise<DiaryRecommendationResponse> => {
  const queryParams = {
    limit: params.limit ?? 10,
    sort_by: params.sort_by ?? 'hybrid',
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    region_id: params.region_id ?? undefined,
  }

  const { data } = await apiClient.get<DiaryRecommendationResponse>(
    '/diaries/recommendations',
    { params: queryParams }
  )

  return data
}

/**
 * Search diaries using full-text search
 */
export const searchDiaries = async (
  query: string,
  params: {
    limit?: number
    sort_by?: DiarySortBy
    interests?: string[]
    region_id?: number
  } = {}
): Promise<DiaryListResponse> => {
  const queryParams = {
    q: query,
    limit: params.limit ?? 20,
    sort_by: params.sort_by ?? 'hybrid',
    interests: params.interests && params.interests.length > 0 ? params.interests : undefined,
    region_id: params.region_id ?? undefined,
  }

  const { data } = await apiClient.get<DiaryListResponse>('/diaries/search', {
    params: queryParams,
  })

  return data
}

/**
 * Get diary detail by ID
 */
export const fetchDiaryDetail = async (diaryId: number): Promise<DiaryDetail> => {
  const { data } = await apiClient.get<DiaryDetail>(`/diaries/${diaryId}`)
  return data
}

/**
 * Create a new diary
 */
export const createDiary = async (
  request: DiaryCreateRequest
): Promise<DiaryCreateResponse> => {
  const { data } = await apiClient.post<DiaryCreateResponse>('/diaries', request)
  return data
}

/**
 * Update an existing diary
 */
export const updateDiary = async (
  diaryId: number,
  request: DiaryUpdateRequest
): Promise<DiaryDetail> => {
  const { data } = await apiClient.put<DiaryDetail>(`/diaries/${diaryId}`, request)
  return data
}

/**
 * Delete a diary
 */
export const deleteDiary = async (diaryId: number): Promise<void> => {
  await apiClient.delete(`/diaries/${diaryId}`)
}

/**
 * Record a diary view
 */
export const recordDiaryView = async (diaryId: number): Promise<void> => {
  await apiClient.post(`/diaries/${diaryId}/view`)
}

/**
 * Rate a diary
 */
export const rateDiary = async (
  diaryId: number,
  request: DiaryRatingRequest
): Promise<DiaryRatingResponse> => {
  const { data } = await apiClient.post<DiaryRatingResponse>(
    `/diaries/${diaryId}/rate`,
    request
  )
  return data
}

/**
 * Generate animation for a diary using AIGC
 */
export const generateDiaryAnimation = async (
  diaryId: number,
  request: AnimationGenerateRequest = {}
): Promise<DiaryAnimation> => {
  const { data } = await apiClient.post<DiaryAnimation>(
    `/diaries/${diaryId}/generate-animation`,
    request
  )
  return data
}

/**
 * Get all animations for a diary
 */
export const fetchDiaryAnimations = async (diaryId: number): Promise<DiaryAnimation[]> => {
  const { data } = await apiClient.get<DiaryAnimation[]>(`/diaries/${diaryId}/animations`)
  return data
}

/**
 * Get user's diaries
 */
export const fetchUserDiaries = async (
  userId: number,
  params: { page?: number; page_size?: number; status?: string } = {}
): Promise<DiaryListResponse> => {
  const queryParams = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 10,
    status: params.status ?? undefined,
  }

  const { data } = await apiClient.get<DiaryListResponse>(`/diaries/users/${userId}/diaries`, {
    params: queryParams,
  })

  return data
}
