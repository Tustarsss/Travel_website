<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import RouteMap from '../components/map/RouteMap.vue'
import {
  fetchRoutePlan,
  fetchNearbyFacilities,
  fetchRegionMapData,
  fetchRegionDetail,
  fetchRegionNodeDetail,
  searchRegionNodes,
  searchRegions,
  type FacilityQuery,
  type RoutePlanQuery,
} from '../services/api'
import type {
  FacilityCategory,
  FacilityRouteItem,
  FacilityRouteResponse,
  MapFeatureCollection,
  RegionNodeSummary,
  RegionSearchResult,
  RegionType,
  RoutePlanResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'
import {
  FACILITY_CATEGORY_LABELS,
  SAMPLE_FACILITY_QUERIES,
  SAMPLE_ROUTING_COMBINATIONS,
  TRANSPORT_MODE_LABELS,
} from '../constants/demoOptions'
import {
  usePreferencesStore,
  createFacilityDefaults,
  createRoutingDefaults,
} from '../stores/preferences'
import type { FacilityPreferences } from '../stores/preferences'
import KeywordSearchSelect from '../components/ui/KeywordSearchSelect.vue'
import { useApiRequest } from '../composables/useApiRequest'

interface RouteFormState {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes: TransportMode[]
}

interface FacilityFormState {
  regionId: number
  originNodeId: number
  radiusMeters: number | null
  limit: number
  strategy: WeightStrategy
  categories: FacilityCategory[]
  transportModes: TransportMode[]
}

type Option<TPayload> = {
  id: number | string
  label: string
  description?: string
  payload?: TPayload
}

type RegionOption = Option<RegionSearchResult>
type NodeOption = Option<RegionNodeSummary>

const regionTypeLabels: Record<RegionType, string> = {
  scenic: '景区',
  campus: '校园',
}

const toRegionOption = (item: RegionSearchResult): RegionOption => {
  const meta = [item.city ?? undefined, item.type ? regionTypeLabels[item.type] : undefined]
    .filter(Boolean)
    .join(' · ')
  return {
    id: item.id,
    label: item.name,
    description: item.description ?? (meta || undefined),
    payload: item,
  }
}

const toNodeOption = (item: RegionNodeSummary): NodeOption => {
  const description =
    item.description ??
    (item.code ? `编号 ${item.code}` : undefined) ??
    (Number.isFinite(item.latitude) && Number.isFinite(item.longitude)
      ? `(${item.latitude?.toFixed(4)}, ${item.longitude?.toFixed(4)})`
      : undefined)

  return {
    id: item.id,
    label: item.name ?? `节点 ${item.id}`,
    description: description ?? undefined,
    payload: item,
  }
}

const routeStrategyOptions: { label: string; value: WeightStrategy }[] = [
  { label: '耗时最短', value: 'time' },
  { label: '距离最短', value: 'distance' },
]

const facilityStrategyOptions: { label: string; value: WeightStrategy }[] = [
  { label: '距离优先', value: 'distance' },
  { label: '时间优先', value: 'time' },
]

const transportModeOptions = computed(() =>
  Object.entries(TRANSPORT_MODE_LABELS).map(([value, label]) => ({
    value: value as TransportMode,
    label,
  }))
)

const facilityCategoryOptions = computed(() =>
  Object.entries(FACILITY_CATEGORY_LABELS).map(([value, label]) => ({
    value: value as FacilityCategory,
    label,
  }))
)

const preferencesStore = usePreferencesStore()
const { routing, facilities } = storeToRefs(preferencesStore)

const routeForm = reactive<RouteFormState>({ ...createRoutingDefaults(), transportModes: [] })
const facilityForm = reactive<FacilityFormState>({ ...createFacilityDefaults(), transportModes: [] })

const syncFacilityWithRoute = ref(true)
const selectedRegion = ref<RegionOption | null>(null)
const selectedStartNode = ref<NodeOption | null>(null)
const selectedEndNode = ref<NodeOption | null>(null)
const selectedFacilityRegion = ref<RegionOption | null>(null)
const selectedFacilityOrigin = ref<NodeOption | null>(null)

const searchRegionOptions = async (keyword: string): Promise<RegionOption[]> => {
  const trimmed = keyword.trim()
  if (!trimmed) return []

  try {
    const items = await searchRegions({ keyword: trimmed, limit: 12 })
    return items.map(toRegionOption)
  } catch (error) {
    console.warn('Failed to search regions:', error)
    return []
  }
}

const createNodeSearchProvider = (getRegionId: () => number) =>
  async (keyword: string): Promise<NodeOption[]> => {
    const trimmed = keyword.trim()
    const regionId = getRegionId()
    if (!trimmed || !regionId) return []

    try {
      const items = await searchRegionNodes({ regionId, keyword: trimmed, limit: 15 })
      return items.map(toNodeOption)
    } catch (error) {
      console.warn('Failed to search nodes:', error)
      return []
    }
  }

const searchStartNodeOptions = createNodeSearchProvider(() => routeForm.regionId)
const searchEndNodeOptions = createNodeSearchProvider(() => routeForm.regionId)
const searchFacilityOriginOptions = createNodeSearchProvider(() => facilityForm.regionId)

const createFallbackRegionOption = (regionId: number): RegionOption => ({
  id: regionId,
  label: `区域 #${regionId}`,
  payload: {
    id: regionId,
    name: `区域 #${regionId}`,
  },
})

const createFallbackNodeOption = (
  regionId: number,
  nodeId: number
): NodeOption => ({
  id: nodeId,
  label: `节点 ${nodeId}`,
  payload: {
    id: nodeId,
    name: `节点 ${nodeId}`,
    region_id: regionId,
  },
})

const handleRegionSelect = (option: any) => {
  const payload = option.payload as RegionSearchResult | undefined
  if (!payload) return
  const regionOption: RegionOption = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }

  selectedRegion.value = regionOption
  const regionId = payload.id
  if (routeForm.regionId !== regionId) {
    routeForm.regionId = regionId
  }
  if (syncFacilityWithRoute.value) {
    facilityForm.regionId = regionId
    selectedFacilityRegion.value = regionOption
  }
}

const handleRegionClear = () => {
  selectedRegion.value = null
  routeForm.regionId = 0
  routeForm.startNodeId = 0
  routeForm.endNodeId = 0
  selectedStartNode.value = null
  selectedEndNode.value = null

  if (syncFacilityWithRoute.value) {
    facilityForm.regionId = 0
    facilityForm.originNodeId = 0
    selectedFacilityRegion.value = null
    selectedFacilityOrigin.value = null
  }
}

const handleStartNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  const nodeOption: NodeOption = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }

  selectedStartNode.value = nodeOption
  routeForm.startNodeId = payload.id
  if (syncFacilityWithRoute.value) {
    facilityForm.originNodeId = payload.id
    selectedFacilityOrigin.value = nodeOption
  }
}

const handleStartNodeClear = () => {
  selectedStartNode.value = null
  routeForm.startNodeId = 0
  if (syncFacilityWithRoute.value) {
    facilityForm.originNodeId = 0
    selectedFacilityOrigin.value = null
  }
}

const handleEndNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedEndNode.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  routeForm.endNodeId = payload.id
}

const handleEndNodeClear = () => {
  selectedEndNode.value = null
  routeForm.endNodeId = 0
}

const handleFacilityRegionSelect = (option: any) => {
  const payload = option.payload as RegionSearchResult | undefined
  if (!payload) return
  const regionOption: RegionOption = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }

  selectedFacilityRegion.value = regionOption
  facilityForm.regionId = payload.id
  if (
    selectedFacilityOrigin.value?.payload &&
    selectedFacilityOrigin.value.payload.region_id !== payload.id
  ) {
    selectedFacilityOrigin.value = null
    facilityForm.originNodeId = 0
  }
}

const handleFacilityRegionClear = () => {
  selectedFacilityRegion.value = null
  facilityForm.regionId = 0
  facilityForm.originNodeId = 0
  selectedFacilityOrigin.value = null
}

const handleFacilityOriginSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedFacilityOrigin.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  facilityForm.originNodeId = payload.id
}

const handleFacilityOriginClear = () => {
  selectedFacilityOrigin.value = null
  facilityForm.originNodeId = 0
}

const hydrateRouteForm = (prefs = routing.value) => {
  routeForm.regionId = prefs.regionId
  routeForm.startNodeId = prefs.startNodeId
  routeForm.endNodeId = prefs.endNodeId
  routeForm.strategy = prefs.strategy
  routeForm.transportModes = [...prefs.transportModes]
}

const hydrateFacilityForm = (prefs = facilities.value) => {
  facilityForm.regionId = prefs.regionId
  facilityForm.originNodeId = prefs.originNodeId
  facilityForm.radiusMeters = prefs.radiusMeters
  facilityForm.limit = prefs.limit
  facilityForm.strategy = prefs.strategy
  facilityForm.categories = [...prefs.categories]
  facilityForm.transportModes = [...prefs.transportModes]
}

const {
  data: routeData,
  error: routeError,
  loading: routeLoading,
  execute: executeRoute,
  reset: resetRouteRequest,
} = useApiRequest(fetchRoutePlan)

const {
  data: facilityData,
  error: facilityError,
  loading: facilityLoading,
  execute: executeFacilities,
  reset: resetFacilitiesRequest,
} = useApiRequest(fetchNearbyFacilities)

watch(
  routing,
  (value) => {
    hydrateRouteForm(value)
  },
  { immediate: true }
)

watch(
  facilities,
  (value) => {
    hydrateFacilityForm(value)
    if (!facilityData.value && typeof window !== 'undefined') {
      void executeFacilities(buildFacilityPayload(value))
    }
  },
  { immediate: true }
)

const loadRegionOption = async (regionId: number): Promise<RegionOption> => {
  try {
    const detail = await fetchRegionDetail(regionId)
    return toRegionOption(detail)
  } catch (error) {
    console.warn('Failed to load region detail:', error)
    return createFallbackRegionOption(regionId)
  }
}

const loadNodeOption = async (
  regionId: number,
  nodeId: number
): Promise<NodeOption> => {
  try {
    const detail = await fetchRegionNodeDetail(regionId, nodeId)
    return toNodeOption(detail)
  } catch (error) {
    console.warn('Failed to load node detail:', error)
    return createFallbackNodeOption(regionId, nodeId)
  }
}

let regionFetchToken = 0
watch(
  () => routeForm.regionId,
  (regionId) => {
    if (!regionId) {
      selectedRegion.value = null
      return
    }
    if (selectedRegion.value?.payload?.id === regionId) return
    regionFetchToken += 1
    const token = regionFetchToken
    void loadRegionOption(regionId).then((option) => {
      if (regionFetchToken === token) {
        selectedRegion.value = option
      }
    })
  },
  { immediate: true }
)

let facilityRegionFetchToken = 0
watch(
  () => facilityForm.regionId,
  (regionId) => {
    if (!regionId) {
      if (!syncFacilityWithRoute.value) {
        selectedFacilityRegion.value = null
      }
      return
    }
    if (selectedFacilityRegion.value?.payload?.id === regionId) return
    facilityRegionFetchToken += 1
    const token = facilityRegionFetchToken
    void loadRegionOption(regionId).then((option) => {
      if (facilityRegionFetchToken === token) {
        selectedFacilityRegion.value = option
      }
    })
  },
  { immediate: true }
)

let startNodeFetchToken = 0
watch(
  () => [routeForm.regionId, routeForm.startNodeId] as const,
  ([regionId, nodeId]) => {
    if (!regionId || !nodeId) {
      if (nodeId === 0) {
        selectedStartNode.value = null
      }
      return
    }
    if (selectedStartNode.value?.payload?.id === nodeId) return
    startNodeFetchToken += 1
    const token = startNodeFetchToken
    void loadNodeOption(regionId, nodeId).then((option) => {
      if (startNodeFetchToken === token) {
        selectedStartNode.value = option
        if (syncFacilityWithRoute.value) {
          selectedFacilityOrigin.value = option
        }
      }
    })
  },
  { immediate: true }
)

let endNodeFetchToken = 0
watch(
  () => [routeForm.regionId, routeForm.endNodeId] as const,
  ([regionId, nodeId]) => {
    if (!regionId || !nodeId) {
      if (nodeId === 0) {
        selectedEndNode.value = null
      }
      return
    }
    if (selectedEndNode.value?.payload?.id === nodeId) return
    endNodeFetchToken += 1
    const token = endNodeFetchToken
    void loadNodeOption(regionId, nodeId).then((option) => {
      if (endNodeFetchToken === token) {
        selectedEndNode.value = option
      }
    })
  },
  { immediate: true }
)

let facilityNodeFetchToken = 0
watch(
  () => [facilityForm.regionId, facilityForm.originNodeId] as const,
  ([regionId, nodeId]) => {
    if (!regionId || !nodeId) {
      if (nodeId === 0) {
        selectedFacilityOrigin.value = null
      }
      return
    }
    if (selectedFacilityOrigin.value?.payload?.id === nodeId) return
    facilityNodeFetchToken += 1
    const token = facilityNodeFetchToken
    void loadNodeOption(regionId, nodeId).then((option) => {
      if (facilityNodeFetchToken === token) {
        selectedFacilityOrigin.value = option
      }
    })
  },
  { immediate: true }
)

const plan = computed<RoutePlanResponse | null>(() => routeData.value ?? null)
const facilityResults = computed<FacilityRouteResponse | null>(() => facilityData.value ?? null)
const facilityItems = computed<FacilityRouteItem[]>(() => facilityResults.value?.items ?? [])
const facilityTotal = computed(() => facilityResults.value?.total ?? 0)
const allowedModes = computed(() => plan.value?.allowed_transport_modes ?? [])

const mapTile = ref<MapFeatureCollection | null>(null)
const mapRegionId = ref<number | null>(null)
const mapLoading = ref(false)
const mapError = ref<string | null>(null)

const ensureMapData = async (regionId: number | null | undefined) => {
  if (!regionId || mapRegionId.value === regionId) return
  mapLoading.value = true
  mapError.value = null
  try {
    mapTile.value = await fetchRegionMapData(regionId)
    mapRegionId.value = regionId
  } catch (error) {
    mapTile.value = null
    mapRegionId.value = null
    mapError.value = error instanceof Error ? error.message : '地图数据加载失败，请稍后重试。'
  } finally {
    mapLoading.value = false
  }
}

const applyRouteContextToFacilities = (value: RoutePlanResponse | null) => {
  if (!value || !syncFacilityWithRoute.value) return
  facilityForm.regionId = value.region_id
  const startNode = value.nodes?.[0]
  if (startNode) {
    facilityForm.originNodeId = startNode.id
  }
}

watch(plan, (value) => {
  if (value) {
    applyRouteContextToFacilities(value)
    void ensureMapData(value.region_id)
  }
})

watch(facilityResults, (value) => {
  if (value) {
    void ensureMapData(value.region_id)
  }
})

watch(syncFacilityWithRoute, (value) => {
  if (value) {
    facilityForm.regionId = routeForm.regionId
    facilityForm.originNodeId = routeForm.startNodeId
    selectedFacilityRegion.value = selectedRegion.value
    selectedFacilityOrigin.value = selectedStartNode.value
    applyRouteContextToFacilities(plan.value)
  }
})

function buildRoutePayload(): RoutePlanQuery {
  return {
    regionId: routeForm.regionId,
    startNodeId: routeForm.startNodeId,
    endNodeId: routeForm.endNodeId,
    strategy: routeForm.strategy,
    transportModes: routeForm.transportModes,
  }
}

function buildFacilityPayload(
  state: FacilityFormState | FacilityPreferences = facilityForm
): FacilityQuery {
  return {
    regionId: state.regionId,
    originNodeId: state.originNodeId,
    radiusMeters: state.radiusMeters ?? undefined,
    limit: state.limit,
    strategy: state.strategy,
    categories: [...state.categories],
    transportModes: [...state.transportModes],
  }
}

const submitRoute = async () => {
  if (!routeForm.regionId || !routeForm.startNodeId || !routeForm.endNodeId) {
    console.warn('请先通过关键词选择完整的区域与起终点。')
    return
  }
  const payload = buildRoutePayload()
  try {
    const result = await executeRoute(payload)
    preferencesStore.updateRouting({
      regionId: payload.regionId,
      startNodeId: payload.startNodeId,
      endNodeId: payload.endNodeId,
      strategy: payload.strategy,
      transportModes: [...(payload.transportModes ?? [])],
    })
    applyRouteContextToFacilities(result)
    await ensureMapData(result.region_id)
    if (syncFacilityWithRoute.value && facilityData.value) {
      await runFacilitySearch({ persist: false })
    }
  } catch {
    // 错误由 useApiRequest 统一处理
  }
}

const runFacilitySearch = async (options: { persist?: boolean } = { persist: true }) => {
  if (!facilityForm.regionId || !facilityForm.originNodeId) {
    console.warn('请先选择设施检索的区域和参考节点。')
    return
  }
  const payload = buildFacilityPayload()
  try {
    await executeFacilities(payload)
    if (options.persist !== false) {
      preferencesStore.updateFacilities({
        regionId: facilityForm.regionId,
        originNodeId: facilityForm.originNodeId,
        radiusMeters: facilityForm.radiusMeters,
        limit: facilityForm.limit,
        strategy: facilityForm.strategy,
        categories: [...facilityForm.categories],
        transportModes: [...facilityForm.transportModes],
      })
    }
  } catch {
    // 错误由 useApiRequest 统一处理
  }
}

const swapRouteNodes = () => {
  const { startNodeId, endNodeId } = routeForm
  routeForm.startNodeId = endNodeId
  routeForm.endNodeId = startNodeId
  const temp = selectedStartNode.value
  selectedStartNode.value = selectedEndNode.value
  selectedEndNode.value = temp
  if (syncFacilityWithRoute.value) {
    facilityForm.originNodeId = routeForm.startNodeId
    selectedFacilityOrigin.value = selectedStartNode.value
  }
}

const resetRouteForm = () => {
  const defaults = createRoutingDefaults()
  hydrateRouteForm(defaults)
  preferencesStore.updateRouting(defaults)
  resetRouteRequest()
  selectedRegion.value = null
  selectedStartNode.value = null
  selectedEndNode.value = null
}

const resetFacilityForm = () => {
  const defaults = createFacilityDefaults()
  hydrateFacilityForm(defaults)
  preferencesStore.updateFacilities(defaults)
  resetFacilitiesRequest()
  selectedFacilityRegion.value = null
  selectedFacilityOrigin.value = null
}

const applyRouteSample = (index: number) => {
  const sample = SAMPLE_ROUTING_COMBINATIONS[index]
  if (!sample) return
  routeForm.regionId = sample.regionId
  routeForm.startNodeId = sample.startNodeId
  routeForm.endNodeId = sample.endNodeId
  selectedRegion.value = null
  selectedStartNode.value = null
  selectedEndNode.value = null
}

const applyFacilitySample = (index: number) => {
  const sample = SAMPLE_FACILITY_QUERIES[index]
  if (!sample) return
  facilityForm.regionId = sample.regionId
  facilityForm.originNodeId = sample.originNodeId
  facilityForm.radiusMeters = sample.radius ?? null
  facilityForm.categories = []
  facilityForm.transportModes = []
  selectedFacilityRegion.value = null
  selectedFacilityOrigin.value = null
}

const handleFacilitySubmit = async () => {
  await runFacilitySearch()
}

</script>

<template>
  <div class="space-y-8">
    <PageSection
      title="出行与设施一体化导航"
      description="先规划关键行程节点，再围绕路线查找可用设施，帮助你快速完成现实场景下的出行准备。"
    >
      <div class="grid gap-6 lg:grid-cols-[minmax(0,1.4fr),minmax(0,1.1fr)]">
        <form class="planning-card" @submit.prevent="submitRoute">
          <header class="card-header">
            <div>
              <h3>路线规划</h3>
              <p>输入起终点节点，选择优化策略与交通方式即可生成最优路线。</p>
            </div>
            <button type="button" class="ghost-button" @click="swapRouteNodes">交换起终点</button>
          </header>
          <div class="form-grid">
            <label>
              <span>目标区域</span>
              <KeywordSearchSelect
                v-model="selectedRegion"
                :search="searchRegionOptions"
                placeholder="输入区域名称或关键词"
                @select="handleRegionSelect"
                @clear="handleRegionClear"
              />
            </label>
            <label>
              <span>起点节点</span>
              <KeywordSearchSelect
                v-model="selectedStartNode"
                :search="searchStartNodeOptions"
                placeholder="输入节点名称或关键词"
                :disabled="!routeForm.regionId"
                @select="handleStartNodeSelect"
                @clear="handleStartNodeClear"
              />
            </label>
            <label>
              <span>终点节点</span>
              <KeywordSearchSelect
                v-model="selectedEndNode"
                :search="searchEndNodeOptions"
                placeholder="输入节点名称或关键词"
                :disabled="!routeForm.regionId"
                @select="handleEndNodeSelect"
                @clear="handleEndNodeClear"
              />
            </label>
            <label>
              <span>优化策略</span>
              <select v-model="routeForm.strategy">
                <option v-for="option in routeStrategyOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>
          <fieldset class="field-group">
            <legend>限定交通方式（可选）</legend>
            <div class="option-chips">
              <label v-for="option in transportModeOptions" :key="option.value">
                <input v-model="routeForm.transportModes" type="checkbox" :value="option.value" class="h-4 w-4" />
                <span>{{ option.label }}</span>
              </label>
            </div>
            <p>若未选择，则默认使用后端允许的全部交通方式。</p>
          </fieldset>
          <div class="quick-actions">
            <span>快速示例</span>
            <div>
              <button
                v-for="(sample, index) in SAMPLE_ROUTING_COMBINATIONS"
                :key="sample.label"
                type="button"
                class="chip"
                @click="applyRouteSample(index)"
              >
                {{ sample.label }}
              </button>
            </div>
          </div>
          <div class="card-actions">
            <button type="submit" class="primary" :disabled="routeLoading">
              {{ routeLoading ? '规划中…' : '计算路线' }}
            </button>
            <button type="button" class="secondary" @click="resetRouteForm">重置参数</button>
          </div>
        </form>

  <form class="planning-card" @submit.prevent="handleFacilitySubmit">
          <header class="card-header">
            <div>
              <h3>沿线设施</h3>
              <p>以路线起点为参照，筛选一定半径内的设施并获取最短到达路线。</p>
            </div>
            <label class="sync-toggle">
              <input v-model="syncFacilityWithRoute" type="checkbox" class="h-4 w-4" />
              <span>跟随路线起点</span>
            </label>
          </header>
          <div class="form-grid">
            <label>
              <span>目标区域</span>
              <KeywordSearchSelect
                v-model="selectedFacilityRegion"
                :search="searchRegionOptions"
                placeholder="输入区域名称或关键词"
                :disabled="syncFacilityWithRoute"
                @select="handleFacilityRegionSelect"
                @clear="handleFacilityRegionClear"
              />
            </label>
            <label>
              <span>参考节点</span>
              <KeywordSearchSelect
                v-model="selectedFacilityOrigin"
                :search="searchFacilityOriginOptions"
                placeholder="输入节点名称或关键词"
                :disabled="!facilityForm.regionId"
                @select="handleFacilityOriginSelect"
                @clear="handleFacilityOriginClear"
              />
            </label>
            <label>
              <span>检索半径（米）</span>
              <input v-model.number="facilityForm.radiusMeters" type="number" min="0" placeholder="默认 500" />
              <small>留空则采用后端默认设置。</small>
            </label>
            <label>
              <span>返回数量</span>
              <input v-model.number="facilityForm.limit" type="number" min="1" max="50" />
            </label>
            <label>
              <span>路线策略</span>
              <select v-model="facilityForm.strategy">
                <option v-for="option in facilityStrategyOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>
          <fieldset class="field-group">
            <legend>设施类别（多选）</legend>
            <div class="option-grid">
              <label v-for="option in facilityCategoryOptions" :key="option.value">
                <input v-model="facilityForm.categories" type="checkbox" :value="option.value" class="h-4 w-4" />
                <span>{{ option.label }}</span>
              </label>
            </div>
            <p>不勾选时默认返回所有类别。</p>
          </fieldset>
          <fieldset class="field-group">
            <legend>交通方式（可选）</legend>
            <div class="option-chips">
              <label v-for="option in transportModeOptions" :key="option.value">
                <input v-model="facilityForm.transportModes" type="checkbox" :value="option.value" class="h-4 w-4" />
                <span>{{ option.label }}</span>
              </label>
            </div>
          </fieldset>
          <div class="quick-actions">
            <span>示例参数</span>
            <div>
              <button
                v-for="(sample, index) in SAMPLE_FACILITY_QUERIES"
                :key="sample.label"
                type="button"
                class="chip"
                @click="applyFacilitySample(index)"
              >
                {{ sample.label }}
              </button>
            </div>
          </div>
          <div class="card-actions">
            <button type="submit" class="primary" :disabled="facilityLoading">
              {{ facilityLoading ? '检索中…' : '查询设施' }}
            </button>
            <button type="button" class="secondary" @click="resetFacilityForm">清空条件</button>
          </div>
        </form>
      </div>
    </PageSection>

    <PageSection
      title="地图总览"
      description="生成的路线、沿线设施和基础路网将同步绘制在地图上，辅助现场调度。"
    >
      <div class="space-y-4">
        <ErrorAlert v-if="mapError" :message="mapError" />
        <RouteMap
          :plan="plan"
          :facilities="facilityItems"
          :tile="mapTile"
          :loading="mapLoading || routeLoading || facilityLoading"
        />
      </div>
    </PageSection>

    <PageSection
      title="结果分析"
      description="查看路线统计指标与设施明细，方便为游客或学生准备更贴近现实的出行方案。"
    >
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.1fr),minmax(0,0.9fr)]">
        <section class="result-card">
          <header>
            <h3>路线详情</h3>
            <span v-if="plan" class="timestamp">
              更新时间：{{ plan.generated_at ? new Date(plan.generated_at).toLocaleString() : '—' }}
            </span>
          </header>
          <template v-if="routeError">
            <ErrorAlert :message="routeError.message" />
          </template>
          <template v-else-if="routeLoading">
            <LoadingIndicator label="正在计算最优路线，请稍候…" />
          </template>
          <template v-else-if="plan">
            <div class="stat-grid">
              <div>
                <p>总距离</p>
                <strong>{{ plan.total_distance.toFixed(2) }} km</strong>
              </div>
              <div>
                <p>总耗时</p>
                <strong>{{ plan.total_time.toFixed(2) }} min</strong>
              </div>
              <div>
                <p>区域</p>
                <strong>{{ selectedRegion?.label ?? `区域 ${plan.region_id}` }}</strong>
              </div>
            </div>
            <div class="mode-list">
              <span>允许交通方式：</span>
              <span
                v-for="mode in allowedModes"
                :key="mode"
                class="chip"
              >
                {{ TRANSPORT_MODE_LABELS[mode as TransportMode] ?? mode }}
              </span>
            </div>
            <div class="detail-panels">
              <div>
                <h4>节点序列</h4>
                <ol>
                  <li v-for="(node, index) in plan.nodes" :key="node.id">
                    <span class="badge">{{ index + 1 }}</span>
                    <div>
                      <strong>{{ node.name ?? `节点 ${node.id}` }}</strong>
                      <small>({{ node.latitude.toFixed(6) }}, {{ node.longitude.toFixed(6) }})</small>
                    </div>
                  </li>
                </ol>
              </div>
              <div>
                <h4>路段详情</h4>
                <ul>
                  <li
                    v-for="segment in plan.segments"
                    :key="`${segment.source_id}-${segment.target_id}-${segment.transport_mode}`"
                  >
                    <div class="segment-head">
                      <span>{{ segment.source_id }} → {{ segment.target_id }}</span>
                      <span class="chip">
                        {{ TRANSPORT_MODE_LABELS[segment.transport_mode as TransportMode] ?? segment.transport_mode }}
                      </span>
                    </div>
                    <div class="segment-meta">
                      <span>距离 {{ segment.distance.toFixed(2) }} km</span>
                      <span>时间 {{ segment.time.toFixed(2) }} min</span>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </template>
          <template v-else>
            <EmptyState
              title="暂无路线规划结果"
              description="请填写上方表单并点击“计算路线”，即可获取详细规划。"
              icon="🛣️"
            />
          </template>
        </section>

        <section class="result-card">
          <header>
            <h3>设施明细</h3>
            <span v-if="facilityResults" class="timestamp">
              {{ selectedFacilityRegion?.label ?? `区域 ${facilityResults.region_id}` }} · 参考节点
              {{ selectedFacilityOrigin?.label ?? `节点 ${facilityResults.origin_node_id}` }}
            </span>
          </header>
          <template v-if="facilityError">
            <ErrorAlert :message="facilityError.message" />
          </template>
          <template v-else-if="facilityLoading">
            <LoadingIndicator label="正在检索附近设施，请稍候…" />
          </template>
          <template v-else-if="facilityItems.length">
            <p class="summary">共找到 {{ facilityTotal }} 个设施，按最优路线距离排序：</p>
            <ul class="facility-list">
              <li v-for="item in facilityItems" :key="item.facility_id">
                <div class="facility-head">
                  <div>
                    <strong>{{ item.name }}</strong>
                    <small>设施 ID：{{ item.facility_id }}</small>
                  </div>
                  <span class="chip">
                    {{ FACILITY_CATEGORY_LABELS[item.category] ?? item.category }}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>直线距离</dt>
                    <dd>{{ item.distance.toFixed(2) }} m</dd>
                  </div>
                  <div>
                    <dt>预计耗时</dt>
                    <dd>{{ item.travel_time.toFixed(2) }} min</dd>
                  </div>
                  <div>
                    <dt>路线策略</dt>
                    <dd>{{ item.strategy === 'distance' ? '距离优先' : '时间优先' }}</dd>
                  </div>
                  <div class="full">
                    <dt>涉及节点</dt>
                    <dd>
                      <span v-for="nodeId in item.node_sequence" :key="nodeId" class="badge">#{{ nodeId }}</span>
                    </dd>
                  </div>
                </dl>
              </li>
            </ul>
          </template>
          <template v-else>
            <EmptyState
              title="暂无设施结果"
              description="调整检索半径或设施类别后再次搜索，或勾选“跟随路线起点”快速套用路线参数。"
              icon="🏙️"
            />
          </template>
        </section>
      </div>
    </PageSection>
  </div>
</template>

<style scoped>
.planning-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
  border-radius: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.88));
  box-shadow: 0 20px 45px -25px rgba(15, 23, 42, 0.4);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.card-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
}

.card-header p {
  margin-top: 0.3rem;
  font-size: 0.85rem;
  color: #64748b;
}

.ghost-button {
  align-self: flex-start;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  color: #475569;
  border: 1px solid rgba(148, 163, 184, 0.35);
  transition: all 0.2s ease;
}

.ghost-button:hover {
  border-color: rgba(59, 130, 246, 0.65);
  color: #1d4ed8;
}

.sync-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: #475569;
}

.form-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  font-size: 0.85rem;
  color: #475569;
}

.form-grid span {
  font-weight: 600;
  color: #1f2937;
}

.form-grid input,
.form-grid select {
  border-radius: 0.65rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  padding: 0.65rem 0.75rem;
  font-size: 0.85rem;
  transition: border-color 0.2s ease;
}

.form-grid input:focus,
.form-grid select:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.7);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.form-grid small {
  font-size: 0.7rem;
  color: #94a3b8;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  font-size: 0.85rem;
  color: #475569;
}

.field-group legend {
  font-weight: 600;
  color: #1f2937;
}

.option-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.8rem;
}

.option-chips label,
.option-grid label {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: #475569;
}

.option-grid {
  display: grid;
  gap: 0.6rem;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #475569;
}

.quick-actions > div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.35rem 0.7rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  background: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
}

.chip:hover {
  background: rgba(59, 130, 246, 0.18);
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.primary,
.secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.55rem 1.1rem;
  border-radius: 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.primary {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  box-shadow: 0 12px 30px -20px rgba(37, 99, 235, 0.9);
  border: none;
}

.primary:hover:enabled {
  background: linear-gradient(135deg, #1d4ed8, #1e3a8a);
}

.primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.secondary {
  color: #475569;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: white;
}

.secondary:hover {
  border-color: rgba(59, 130, 246, 0.55);
  color: #1d4ed8;
}

.result-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 40px -32px rgba(15, 23, 42, 0.45);
}

.result-card > header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.result-card h3 {
  font-size: 1.05rem;
  font-weight: 600;
  color: #0f172a;
}

.timestamp {
  font-size: 0.75rem;
  color: #64748b;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}

.stat-grid div {
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  background: rgba(241, 245, 249, 0.8);
  text-align: center;
}

.stat-grid p {
  margin-bottom: 0.35rem;
  font-size: 0.7rem;
  color: #64748b;
  letter-spacing: 0.02em;
}

.stat-grid strong {
  font-size: 1.2rem;
  color: #0f172a;
}

.mode-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.8rem;
  color: #475569;
}

.detail-panels {
  display: grid;
  gap: 1rem;
}

.detail-panels h4 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.65rem;
}

.detail-panels ol {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.detail-panels li {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  padding: 0.65rem 0.8rem;
  border-radius: 1rem;
  background: rgba(248, 250, 252, 0.8);
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.75rem;
  border-radius: 9999px;
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
  font-size: 0.75rem;
  font-weight: 600;
}

.detail-panels ul {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.detail-panels li ul,
.detail-panels li dl {
  margin: 0;
}

.detail-panels li ul li {
  background: transparent;
}

.segment-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #1f2937;
}

.segment-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.35rem;
}

.facility-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.facility-list li {
  padding: 1rem;
  border-radius: 1.25rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(248, 250, 252, 0.85);
}

.facility-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.facility-head strong {
  font-size: 0.95rem;
  color: #0f172a;
}

.facility-head small {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.7rem;
  color: #94a3b8;
}

.facility-list dl {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.65rem 0.85rem;
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #475569;
}

.facility-list dt {
  font-size: 0.7rem;
  color: #94a3b8;
}

.facility-list dd {
  font-weight: 600;
  color: #1f2937;
}

.facility-list .full {
  grid-column: 1 / -1;
}

.facility-list .full dd {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.summary {
  font-size: 0.8rem;
  color: #475569;
}

.segment-meta span::before,
.facility-list dd span::before {
  content: '';
}

.card-actions {
  margin-top: auto;
}

@media (max-width: 1024px) {
  .planning-card {
    border-radius: 1.25rem;
  }
}
</style>
