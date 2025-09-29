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

export const fetchRegionMapData = async (regionId: number): Promise<MapFeatureCollection> => {
  const { data } = await apiClient.get<MapFeatureCollection>(`/map-data/${regionId}`)
  return data
}
