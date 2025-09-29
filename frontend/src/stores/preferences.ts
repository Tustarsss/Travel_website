import { computed, reactive } from 'vue'
import { defineStore } from 'pinia'
import type { FacilityCategory, RecommendationSort, RegionType, TransportMode, WeightStrategy } from '../types/api'

export interface RecommendationPreferences {
  limit: number
  sortBy: RecommendationSort
  interests: string[]
  interestsOnly: boolean
  search: string
  regionType: RegionType | ''
}

export interface RoutingPreferences {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes: TransportMode[]
}

export interface FacilityPreferences {
  regionId: number
  originNodeId: number
  radiusMeters: number | null
  limit: number
  strategy: WeightStrategy
  categories: FacilityCategory[]
  transportModes: TransportMode[]
}

interface PreferencesState {
  recommendation: RecommendationPreferences
  routing: RoutingPreferences
  facilities: FacilityPreferences
}

const STORAGE_KEY = 'travel-preferences-v1'

export const createRecommendationDefaults = (): RecommendationPreferences => ({
  limit: 10,
  sortBy: 'hybrid',
  interests: [],
  interestsOnly: false,
  search: '',
  regionType: '',
})

export const createRoutingDefaults = (): RoutingPreferences => ({
  regionId: 1,
  startNodeId: 1,
  endNodeId: 2,
  strategy: 'time',
  transportModes: [],
})

export const createFacilityDefaults = (): FacilityPreferences => ({
  regionId: 1,
  originNodeId: 1,
  radiusMeters: 500,
  limit: 10,
  strategy: 'distance',
  categories: [],
  transportModes: [],
})

const defaultState = (): PreferencesState => ({
  recommendation: createRecommendationDefaults(),
  routing: createRoutingDefaults(),
  facilities: createFacilityDefaults(),
})

const loadFromStorage = (): PreferencesState => {
  if (typeof window === 'undefined') {
    return defaultState()
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return defaultState()
    }
    const parsed = JSON.parse(raw) as Partial<PreferencesState>
    const defaults = defaultState()
    return {
      recommendation: { ...defaults.recommendation, ...parsed.recommendation },
      routing: { ...defaults.routing, ...parsed.routing },
      facilities: { ...defaults.facilities, ...parsed.facilities },
    }
  } catch (error) {
    console.warn('Failed to parse persisted preferences, falling back to defaults.', error)
    return defaultState()
  }
}

const persistState = (state: PreferencesState) => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (error) {
    console.warn('Failed to persist preferences to localStorage.', error)
  }
}

export const usePreferencesStore = defineStore('preferences', () => {
  const state = reactive<PreferencesState>(loadFromStorage())

  const recommendation = computed(() => state.recommendation)
  const routing = computed(() => state.routing)
  const facilities = computed(() => state.facilities)

  const updateRecommendation = (payload: Partial<RecommendationPreferences>) => {
    Object.assign(state.recommendation, payload)
    persistState(state)
  }

  const updateRouting = (payload: Partial<RoutingPreferences>) => {
    Object.assign(state.routing, payload)
    persistState(state)
  }

  const updateFacilities = (payload: Partial<FacilityPreferences>) => {
    Object.assign(state.facilities, payload)
    persistState(state)
  }

  const resetAll = () => {
    const defaults = defaultState()
    Object.assign(state.recommendation, defaults.recommendation)
    Object.assign(state.routing, defaults.routing)
    Object.assign(state.facilities, defaults.facilities)
    persistState(state)
  }

  return {
    recommendation,
    routing,
    facilities,
    updateRecommendation,
    updateRouting,
    updateFacilities,
    resetAll,
  }
})
