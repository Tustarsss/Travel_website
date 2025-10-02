<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import RouteMap from '../components/map/RouteMap.vue'
import KeywordSearchSelect from '../components/ui/KeywordSearchSelect.vue'
import {
  fetchRoutePlan,
  fetchRegionMapData,
  searchRegionNodes,
  searchRegions,
  type RoutePlanQuery,
} from '../services/api'
import type {
  MapFeatureCollection,
  RegionNodeSummary,
  RegionSearchResult,
  RegionType,
  RoutePlanResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'
import {
  SAMPLE_ROUTING_COMBINATIONS,
  TRANSPORT_MODE_LABELS,
} from '../constants/demoOptions'
import {
  usePreferencesStore,
  createRoutingDefaults,
} from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

interface RouteFormState {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
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
  { label: '⚡ 耗时最短', value: 'time' },
  { label: '📏 距离最短', value: 'distance' },
]

const transportModeOptions = computed(() =>
  Object.entries(TRANSPORT_MODE_LABELS).map(([value, label]) => ({
    value: value as TransportMode,
    label,
  }))
)

const preferencesStore = usePreferencesStore()
const { routing } = storeToRefs(preferencesStore)

const routeForm = reactive<RouteFormState>({ ...createRoutingDefaults(), transportModes: [] })

const selectedRegion = ref<RegionOption | null>(null)
const selectedStartNode = ref<NodeOption | null>(null)
const selectedEndNode = ref<NodeOption | null>(null)

// 搜索函数
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

// 选择处理
const handleRegionSelect = (option: any) => {
  const payload = option.payload as RegionSearchResult | undefined
  if (!payload) return
  selectedRegion.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  const regionId = payload.id
  if (routeForm.regionId !== regionId) {
    routeForm.regionId = regionId
    selectedStartNode.value = null
    selectedEndNode.value = null
    routeForm.startNodeId = 0
    routeForm.endNodeId = 0
  }
}

const handleRegionClear = () => {
  selectedRegion.value = null
  routeForm.regionId = 0
  routeForm.startNodeId = 0
  routeForm.endNodeId = 0
  selectedStartNode.value = null
  selectedEndNode.value = null
}

const handleStartNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedStartNode.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  routeForm.startNodeId = payload.id
}

const handleStartNodeClear = () => {
  selectedStartNode.value = null
  routeForm.startNodeId = 0
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

// 状态管理
const hydrateRouteForm = (prefs = routing.value) => {
  routeForm.regionId = prefs.regionId
  routeForm.startNodeId = prefs.startNodeId
  routeForm.endNodeId = prefs.endNodeId
  routeForm.strategy = prefs.strategy
  routeForm.transportModes = [...prefs.transportModes]
}

watch(routing, (value) => {
  hydrateRouteForm(value)
}, { immediate: true })

// API 请求
const {
  data: routeData,
  error: routeError,
  loading: routeLoading,
  execute: executeRoute,
  reset: resetRouteRequest,
} = useApiRequest(fetchRoutePlan)

const plan = computed<RoutePlanResponse | null>(() => routeData.value ?? null)
const allowedModes = computed(() => plan.value?.allowed_transport_modes ?? [])

// 地图数据
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
    mapError.value = error instanceof Error ? error.message : '地图数据加载失败'
  } finally {
    mapLoading.value = false
  }
}

watch(plan, (value) => {
  if (value) {
    void ensureMapData(value.region_id)
  }
})

// 提交路线规划
const submitRoute = async () => {
  if (!routeForm.regionId || !routeForm.startNodeId || !routeForm.endNodeId) {
    return
  }
  const payload: RoutePlanQuery = {
    regionId: routeForm.regionId,
    startNodeId: routeForm.startNodeId,
    endNodeId: routeForm.endNodeId,
    strategy: routeForm.strategy,
    transportModes: routeForm.transportModes,
  }
  try {
    const result = await executeRoute(payload)
    preferencesStore.updateRouting({
      regionId: payload.regionId,
      startNodeId: payload.startNodeId,
      endNodeId: payload.endNodeId,
      strategy: payload.strategy,
      transportModes: [...(payload.transportModes ?? [])],
    })
    await ensureMapData(result.region_id)
  } catch {
    // 错误由 useApiRequest 处理
  }
}

// 辅助功能
const swapRouteNodes = () => {
  const { startNodeId, endNodeId } = routeForm
  routeForm.startNodeId = endNodeId
  routeForm.endNodeId = startNodeId
  const temp = selectedStartNode.value
  selectedStartNode.value = selectedEndNode.value
  selectedEndNode.value = temp
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

const applySample = (index: number) => {
  const sample = SAMPLE_ROUTING_COMBINATIONS[index]
  if (!sample) return
  routeForm.regionId = sample.regionId
  routeForm.startNodeId = sample.startNodeId
  routeForm.endNodeId = sample.endNodeId
  selectedRegion.value = null
  selectedStartNode.value = null
  selectedEndNode.value = null
}
</script>

<template>
  <div class="space-y-8">
    <!-- 路线规划表单 -->
    <PageSection
      title="旅游路线规划"
      description="进入景区或学校后，输入起点和终点，系统会为您规划最优旅游线路。支持最短距离、最短时间等多种策略，可选择不同交通工具。"
    >
      <form class="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg" @submit.prevent="submitRoute">
        <div class="space-y-5">
          <!-- 区域选择 -->
          <div class="grid gap-5 md:grid-cols-2">
            <div class="space-y-2 md:col-span-2">
              <label class="text-sm font-semibold text-slate-700">
                <span class="flex items-center gap-2">🏛️ 目标区域</span>
              </label>
              <KeywordSearchSelect
                v-model="selectedRegion"
                :search="searchRegionOptions"
                placeholder="输入区域名称或关键词搜索"
                @select="handleRegionSelect"
                @clear="handleRegionClear"
              />
            </div>

            <!-- 起点终点 -->
            <div class="space-y-2">
              <label class="text-sm font-semibold text-slate-700">
                <span class="flex items-center gap-2">📍 起点节点</span>
              </label>
              <KeywordSearchSelect
                v-model="selectedStartNode"
                :search="searchStartNodeOptions"
                placeholder="输入起点节点名称"
                :disabled="!routeForm.regionId"
                @select="handleStartNodeSelect"
                @clear="handleStartNodeClear"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-semibold text-slate-700">
                <span class="flex items-center gap-2">🎯 终点节点</span>
              </label>
              <KeywordSearchSelect
                v-model="selectedEndNode"
                :search="searchEndNodeOptions"
                placeholder="输入终点节点名称"
                :disabled="!routeForm.regionId"
                @select="handleEndNodeSelect"
                @clear="handleEndNodeClear"
              />
            </div>

            <!-- 策略选择 -->
            <div class="space-y-2">
              <label class="text-sm font-semibold text-slate-700">
                <span class="flex items-center gap-2">🎯 优化策略</span>
              </label>
              <select v-model="routeForm.strategy" class="w-full rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary">
                <option v-for="option in routeStrategyOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <!-- 交换起终点按钮 -->
            <div class="flex items-end">
              <button
                type="button"
                class="w-full rounded-xl border-2 border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-primary hover:bg-primary/5"
                @click="swapRouteNodes"
                :disabled="!routeForm.startNodeId || !routeForm.endNodeId"
              >
                🔄 交换起终点
              </button>
            </div>
          </div>

          <!-- 交通方式 -->
          <fieldset class="space-y-3">
            <legend class="text-sm font-semibold text-slate-700">🚗 交通方式（可选）</legend>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="option in transportModeOptions"
                :key="option.value"
                class="inline-flex items-center gap-2 rounded-lg border-2 border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-primary hover:bg-primary/5"
              >
                <input v-model="routeForm.transportModes" type="checkbox" :value="option.value" class="h-4 w-4 rounded border-2 text-primary" />
                {{ option.label }}
              </label>
            </div>
            <p class="text-xs font-medium text-slate-500">💡 不选择则使用后端允许的所有交通方式</p>
          </fieldset>

          <!-- 快速示例 -->
          <div class="rounded-xl bg-slate-50 p-4 space-y-3">
            <span class="text-xs font-semibold text-slate-600">⚡ 快速示例</span>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="(sample, index) in SAMPLE_ROUTING_COMBINATIONS"
                :key="sample.label"
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm transition hover:border-primary hover:text-primary hover:shadow"
                @click="applySample(index)"
              >
                {{ sample.label }}
              </button>
            </div>
          </div>

          <!-- 提交按钮 -->
          <div class="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
            <button
              type="submit"
              class="rounded-xl bg-gradient-to-r from-blue-500 to-primary px-6 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/30 transition hover:shadow-xl hover:shadow-blue-500/40 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none"
              :disabled="routeLoading || !routeForm.regionId || !routeForm.startNodeId || !routeForm.endNodeId"
            >
              {{ routeLoading ? '🔄 规划中…' : '🗺️ 计算路线' }}
            </button>
            <button
              type="button"
              class="rounded-xl border-2 border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-600 transition hover:border-primary hover:text-primary"
              @click="resetRouteForm"
            >
              🔄 重置参数
            </button>
          </div>
        </div>
      </form>
    </PageSection>

    <!-- 地图展示 -->
    <PageSection
      title="地图总览"
      description="生成的路线将在地图上展示，包括途经节点和路段信息。"
    >
      <div class="space-y-4">
        <ErrorAlert v-if="mapError" :message="mapError" />
        <RouteMap
          :plan="plan"
          :tile="mapTile"
          :loading="mapLoading || routeLoading"
        />
      </div>
    </PageSection>

    <!-- 路线详情 -->
    <PageSection
      title="路线详情"
      description="查看路线的详细统计信息和途经节点。"
    >
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg">
        <template v-if="routeError">
          <ErrorAlert :message="routeError.message" />
        </template>
        <template v-else-if="routeLoading">
          <LoadingIndicator label="正在计算最优路线，请稍候…" />
        </template>
        <template v-else-if="plan">
          <div class="space-y-6">
            <!-- 统计信息 -->
            <div class="grid gap-4 sm:grid-cols-3">
              <div class="rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 p-5 text-center">
                <p class="mb-2 text-xs font-semibold text-blue-600">📏 总距离</p>
                <p class="text-2xl font-bold text-blue-900">
                  {{ plan.total_distance.toFixed(2) }} <span class="text-sm font-normal">km</span>
                </p>
              </div>
              <div class="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 p-5 text-center">
                <p class="mb-2 text-xs font-semibold text-emerald-600">⏱️ 总耗时</p>
                <p class="text-2xl font-bold text-emerald-900">
                  {{ plan.total_time.toFixed(2) }} <span class="text-sm font-normal">min</span>
                </p>
              </div>
              <div class="rounded-xl bg-gradient-to-br from-purple-50 to-purple-100 p-5 text-center">
                <p class="mb-2 text-xs font-semibold text-purple-600">🏛️ 区域</p>
                <p class="text-lg font-bold text-purple-900">
                  {{ selectedRegion?.label ?? `区域 ${plan.region_id}` }}
                </p>
              </div>
            </div>

            <!-- 交通方式 -->
            <div class="rounded-xl bg-slate-50 p-4">
              <p class="mb-3 text-sm font-semibold text-slate-700">🚗 允许的交通方式</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="mode in allowedModes"
                  :key="mode"
                  class="inline-flex items-center rounded-lg bg-blue-100 px-3 py-1.5 text-xs font-semibold text-blue-700"
                >
                  {{ TRANSPORT_MODE_LABELS[mode as TransportMode] ?? mode }}
                </span>
              </div>
            </div>

            <!-- 路线提示 -->
            <div class="rounded-xl bg-blue-50 p-4 text-sm text-blue-700">
              <p class="font-medium">
                💡 <strong>提示：</strong>详细的节点和路段信息已在地图上标注，不同的交通方式会以对应颜色高亮显示。
              </p>
            </div>

            <!-- 更新时间 -->
            <p class="text-center text-xs text-slate-500">
              更新时间：{{ plan.generated_at ? new Date(plan.generated_at).toLocaleString() : '—' }}
            </p>
          </div>
        </template>
        <template v-else>
          <EmptyState
            title="暂无路线规划结果"
            description="请填写上方表单并点击计算路线按钮，即可获取详细规划。"
            icon="🗺️"
          />
        </template>
      </div>
    </PageSection>
  </div>
</template>
