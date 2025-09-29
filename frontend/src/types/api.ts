export type RecommendationSort = 'hybrid' | 'popularity' | 'rating'
export type RegionType = 'scenic' | 'campus'

export interface RegionSummary {
  id: number
  name: string
  type: RegionType
  popularity: number
  rating: number
  city?: string | null
  description?: string | null
}

export interface RegionRecommendationItem {
  region: RegionSummary
  score: number
  base_score: number
  interest_matches: string[]
}

export interface RegionRecommendationResponse {
  items: RegionRecommendationItem[]
  sort_by: RecommendationSort
  generated_at: string
  limit: number
  total_candidates: number
  query?: string | null
  interests: string[]
  data_source: string
}

export type WeightStrategy = 'distance' | 'time'
export type TransportMode = 'walk' | 'bike' | 'electric_cart'

export interface RouteNode {
  id: number
  name?: string | null
  latitude: number
  longitude: number
}

export interface RouteSegment {
  source_id: number
  target_id: number
  transport_mode: TransportMode | string
  distance: number
  time: number
}

export interface RoutePlanResponse {
  region_id: number
  strategy: WeightStrategy
  total_distance: number
  total_time: number
  nodes: RouteNode[]
  segments: RouteSegment[]
  generated_at: string
  allowed_transport_modes: TransportMode[] | string[]
}

export type FacilityCategory =
  | 'restroom'
  | 'restaurant'
  | 'shop'
  | 'supermarket'
  | 'cafe'
  | 'atm'
  | 'medical'
  | 'parking'
  | 'information'
  | 'service'

export interface FacilityRouteItem {
  facility_id: number
  name: string
  category: FacilityCategory
  latitude: number
  longitude: number
  distance: number
  travel_time: number
  node_sequence: number[]
  strategy: WeightStrategy
}

export interface FacilityRouteResponse {
  region_id: number
  origin_node_id: number
  radius_meters: number | null
  items: FacilityRouteItem[]
  total: number
}
