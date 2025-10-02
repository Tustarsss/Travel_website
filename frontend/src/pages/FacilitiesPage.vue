<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import KeywordSearchSelect from '../components/ui/KeywordSearchSelect.vue'
import { fetchNearbyFacilities, searchRegionNodes, searchRegions } from '../services/api'
import type {
  FacilityCategory,
  FacilityRouteItem,
  FacilityRouteResponse,
  RegionNodeSummary,
  RegionSearchResult,
} from '../types/api'
import {
  FACILITY_CATEGORY_LABELS,
  SAMPLE_FACILITY_QUERIES,
} from '../constants/demoOptions'
import { usePreferencesStore, createFacilityDefaults } from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

type Option<TPayload> = {
  id: number | string
  label: string
  description?: string
  payload?: TPayload
}

type RegionOption = Option<RegionSearchResult>
type NodeOption = Option<RegionNodeSummary>

interface FacilityFormState {
  regionId: number
  originNodeId: number
  radiusMeters: number | null
  limit: number
  categories: FacilityCategory[]
}

const preferencesStore = usePreferencesStore()
const { facilities } = storeToRefs(preferencesStore)

const form = reactive<FacilityFormState>({
  regionId: 1,
  originNodeId: 1,
  radiusMeters: 500,
  limit: 10,
  categories: [],
})

const facilityCategoryOptions = computed(() =>
  Object.entries(FACILITY_CATEGORY_LABELS).map(([value, label]) => ({
    value: value as FacilityCategory,
    label,
  }))
)

// 搜索相关状态
const selectedRegion = ref<RegionOption | null>(null)
const selectedOriginNode = ref<NodeOption | null>(null)
const categorySearchTerm = ref('')

// 转换函数
const toRegionOption = (item: RegionSearchResult): RegionOption => ({
  id: item.id,
  label: item.name,
  description: item.description ?? `${item.city ?? ''} · ${item.type === 'scenic' ? '景区' : '校园'}`.trim(),
  payload: item,
})

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

const searchOriginNodeOptions = async (keyword: string): Promise<NodeOption[]> => {
  const trimmed = keyword.trim()
  const regionId = form.regionId
  if (!trimmed || !regionId) return []
  try {
    const items = await searchRegionNodes({ regionId, keyword: trimmed, limit: 15 })
    return items.map(toNodeOption)
  } catch (error) {
    console.warn('Failed to search nodes:', error)
    return []
  }
}

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
  if (form.regionId !== regionId) {
    form.regionId = regionId
    selectedOriginNode.value = null
    form.originNodeId = 0
  }
}

const handleRegionClear = () => {
  selectedRegion.value = null
  form.regionId = 0
  form.originNodeId = 0
  selectedOriginNode.value = null
}

const handleOriginNodeSelect = (option: any) => {
  const payload = option.payload as RegionNodeSummary | undefined
  if (!payload) return
  selectedOriginNode.value = {
    id: option.id,
    label: option.label,
    description: option.description,
    payload,
  }
  form.originNodeId = payload.id
}

const handleOriginNodeClear = () => {
  selectedOriginNode.value = null
  form.originNodeId = 0
}

// 类别搜索过滤
const filteredCategoryOptions = computed(() => {
  const term = categorySearchTerm.value.toLowerCase().trim()
  if (!term) return facilityCategoryOptions.value
  return facilityCategoryOptions.value.filter(
    (option) => 
      option.label.toLowerCase().includes(term) ||
      option.value.toLowerCase().includes(term)
  )
})

const buildPayload = () => ({
  regionId: form.regionId,
  originNodeId: form.originNodeId,
  radiusMeters: form.radiusMeters ?? undefined,
  limit: 10, // 固定返回10个结果
  strategy: 'distance' as const, // 固定使用距离优先（步行距离）
  categories: form.categories,
})

const { data, error, loading, execute } = useApiRequest(fetchNearbyFacilities)

const hydrateForm = (prefs = facilities.value) => {
  form.regionId = prefs.regionId
  form.originNodeId = prefs.originNodeId
  form.radiusMeters = prefs.radiusMeters
  // form.limit 不再从偏好设置中恢复，始终使用默认值 10
  form.categories = [...prefs.categories]
}

watch(
  facilities,
  (value) => {
    hydrateForm(value)
    if (!data.value && typeof window !== 'undefined') {
      void execute(buildPayload())
    }
  },
  { immediate: true }
)

const runQuery = async () => {
  const payload = buildPayload()
  await execute(payload)
  preferencesStore.updateFacilities({
    regionId: form.regionId,
    originNodeId: form.originNodeId,
    radiusMeters: form.radiusMeters,
    limit: 10, // 固定保存为 10
    strategy: 'distance', // 固定为距离优先
    categories: [...form.categories],
    transportModes: [], // 不再使用交通方式
  })
}

const applySample = (index: number) => {
  const sample = SAMPLE_FACILITY_QUERIES[index]
  if (!sample) return
  form.regionId = sample.regionId
  form.originNodeId = sample.originNodeId
  form.radiusMeters = sample.radius
  // 清空搜索组件，因为我们直接使用ID
  selectedRegion.value = null
  selectedOriginNode.value = null
}

const resetFilters = () => {
  const defaults = createFacilityDefaults()
  preferencesStore.updateFacilities(defaults)
  hydrateForm(defaults)
  // 清空搜索组件
  selectedRegion.value = null
  selectedOriginNode.value = null
  categorySearchTerm.value = ''
}

const results = computed<FacilityRouteResponse | null>(() => data.value ?? null)
const facilityItems = computed<FacilityRouteItem[]>(() => results.value?.items ?? [])
const totalFacilities = computed(() => results.value?.total ?? 0)
</script>

<template>
  <div class="space-y-6">
    <!-- 功能说明卡片 -->
    <div class="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 to-cyan-50 p-6 shadow-lg">
      <div class="flex items-start gap-4">
        <div class="flex-shrink-0 rounded-xl bg-blue-500 p-3 text-3xl">
          🏙️
        </div>
        <div class="flex-1 space-y-2">
          <h2 class="text-xl font-bold text-slate-900">场所查询功能</h2>
          <p class="text-sm leading-relaxed text-slate-700">
            在景区或学校内部时，选中某个景点或场所作为起点，系统会找出附近一定范围内的超市、卫生间、餐厅等服务设施，
            <strong class="text-blue-700">并根据实际步行距离（而非直线距离）进行排序</strong>。
          </p>
          <div class="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
            <div class="flex items-center gap-2">
              <span class="text-green-600">✓</span>
              <span>按实际路径距离排序</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-green-600">✓</span>
              <span>按设施类别过滤</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-green-600">✓</span>
              <span>支持多种交通方式</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-green-600">✓</span>
              <span>显示预计到达时间</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <PageSection
      title="查询条件"
      description="选择起点位置和设施类别，系统将按照路径距离（非直线距离）为您排序最近的服务设施。"
    >
      <form class="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg" @submit.prevent="runQuery">
        <div class="grid gap-5 md:grid-cols-2">
          <div class="flex flex-col gap-2">
            <label class="text-sm font-semibold text-slate-700">
              <span class="flex items-center gap-2">🏛️ 所在景区/学校</span>
            </label>
            <KeywordSearchSelect
              v-model="selectedRegion"
              :search="searchRegionOptions"
              placeholder="输入景区或学校名称搜索"
              empty-text="输入至少2个字符开始搜索"
              no-results-text="未找到匹配的景区/学校"
              @select="handleRegionSelect"
              @clear="handleRegionClear"
            />
            <p v-if="form.regionId" class="text-xs text-slate-500">
              已选区域ID: {{ form.regionId }}
            </p>
          </div>

          <div class="flex flex-col gap-2">
            <label class="text-sm font-semibold text-slate-700">
              <span class="flex items-center gap-2">📍 当前位置/景点</span>
            </label>
            <KeywordSearchSelect
              v-model="selectedOriginNode"
              :search="searchOriginNodeOptions"
              placeholder="输入景点或位置名称搜索"
              empty-text="请先选择景区，然后输入关键词"
              no-results-text="未找到匹配的位置节点"
              :disabled="!form.regionId"
              @select="handleOriginNodeSelect"
              @clear="handleOriginNodeClear"
            />
            <p v-if="form.originNodeId" class="text-xs text-slate-500">
              已选节点ID: {{ form.originNodeId }}
            </p>
          </div>

          <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700 md:col-span-2">
            <span class="flex items-center gap-2">📏 搜索半径（米）</span>
            <input 
              v-model.number="form.radiusMeters" 
              type="number" 
              min="0"
              class="rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary"
              placeholder="留空使用默认值"
            />
            <span class="text-xs font-normal text-slate-500">留空表示由后端采用默认半径。结果将按步行距离自动排序。</span>
          </label>

          <fieldset class="flex flex-col gap-3 md:col-span-2">
            <legend class="text-sm font-semibold text-slate-700">
              🏷️ 设施类别筛选（多选）
              <span class="ml-2 text-xs font-normal text-slate-500">
                - 可通过类别名称过滤服务设施
              </span>
            </legend>
            
            <!-- 类别搜索框 -->
            <div class="relative">
              <input
                v-model="categorySearchTerm"
                type="text"
                placeholder="🔍 搜索类别..."
                class="w-full rounded-xl border-2 border-slate-200 bg-slate-50 px-4 py-2.5 text-sm transition focus:border-primary focus:bg-white"
              />
              <button
                v-if="categorySearchTerm"
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                @click="categorySearchTerm = ''"
              >
                ✕
              </button>
            </div>

            <!-- 显示搜索结果提示 -->
            <div v-if="categorySearchTerm && filteredCategoryOptions.length === 0" class="text-sm text-amber-600">
              未找到匹配的类别
            </div>
            <div v-else-if="categorySearchTerm" class="text-xs text-blue-600">
              找到 {{ filteredCategoryOptions.length }} 个匹配类别
            </div>

            <!-- 类别选项 -->
            <div class="grid grid-cols-2 gap-3 text-sm font-medium text-slate-700 md:grid-cols-4">
              <label 
                v-for="option in filteredCategoryOptions" 
                :key="option.value" 
                class="inline-flex items-center gap-2 rounded-lg border-2 border-slate-200 bg-slate-50 px-3 py-2 transition hover:border-primary hover:bg-primary/5 cursor-pointer"
              >
                <input v-model="form.categories" type="checkbox" :value="option.value" class="h-4 w-4 rounded border-2 text-primary cursor-pointer" />
                {{ option.label }}
              </label>
            </div>
            <div class="rounded-lg bg-blue-50 p-3 text-xs text-blue-700">
              <p class="font-semibold">💡 使用提示：</p>
              <ul class="mt-1 space-y-1 pl-4">
                <li>• 不选择任何类别：查询所有类型的服务设施</li>
                <li>• 选择一个或多个类别：只显示选中类别的设施</li>
                <li>• 结果将按照<strong>实际步行距离</strong>自动排序（非直线距离）</li>
              </ul>
            </div>
          </fieldset>

          <div class="flex flex-col gap-3 rounded-xl bg-slate-50 p-4 md:col-span-2">
            <span class="text-xs font-semibold text-slate-600">⚡ 快速示例</span>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="(sample, index) in SAMPLE_FACILITY_QUERIES"
                :key="sample.label"
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm transition hover:border-primary hover:text-primary hover:shadow"
                @click="applySample(index)"
              >
                {{ sample.label }}
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5 md:col-span-2">
            <button
              type="submit"
              class="rounded-xl bg-gradient-to-r from-emerald-500 to-green-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-500/30 transition hover:shadow-xl hover:shadow-emerald-500/40 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none"
              :disabled="loading"
            >
              {{ loading ? '🔄 搜索中…' : '🔍 查询设施' }}
            </button>
            <button
              type="button"
              class="rounded-xl border-2 border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-600 transition hover:border-primary hover:text-primary"
              @click="resetFilters"
            >
              🔄 重置条件
            </button>
          </div>
        </div>
      </form>
    </PageSection>

    <PageSection
      title="查询结果"
      :description="
        results
          ? `共找到 ${totalFacilities} 个设施，已按步行距离自动排序（最近的在前）`
          : '提交查询条件后，系统将按照实际步行路径距离为您排序最近的服务设施。'
      "
    >
      <template v-if="error">
        <ErrorAlert :message="error.message" />
      </template>
      <template v-else-if="loading">
        <LoadingIndicator label="正在检索附近设施并计算路径距离，请稍候…" />
      </template>
      <template v-else-if="facilityItems.length">
        <!-- 查询信息卡片 -->
        <div class="mb-5 rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50 to-blue-50 p-4">
          <div class="grid gap-4 text-sm md:grid-cols-3">
            <div class="flex items-center gap-3">
              <div class="flex-shrink-0 rounded-lg bg-blue-500 p-2 text-white">
                🏛️
              </div>
              <div>
                <p class="text-xs text-slate-500">查询区域</p>
                <p class="font-semibold text-slate-900">区域 #{{ results?.region_id }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="flex-shrink-0 rounded-lg bg-emerald-500 p-2 text-white">
                📍
              </div>
              <div>
                <p class="text-xs text-slate-500">起点节点</p>
                <p class="font-semibold text-slate-900">节点 #{{ results?.origin_node_id }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="flex-shrink-0 rounded-lg bg-purple-500 p-2 text-white">
                📏
              </div>
              <div>
                <p class="text-xs text-slate-500">搜索半径</p>
                <p class="font-semibold text-slate-900">
                  {{ results?.radius_meters ? `${results?.radius_meters} 米` : '默认范围' }}
                </p>
              </div>
            </div>
          </div>
          
          <!-- 排序说明 -->
          <div class="mt-4 flex items-start gap-2 rounded-lg bg-green-50 p-3 text-xs text-green-700">
            <span class="flex-shrink-0 text-base">✓</span>
            <div>
              <p class="font-semibold">按步行距离排序</p>
              <p class="mt-1">
                下方设施已按照从起点出发的<strong>实际步行路径距离</strong>由近到远排序，
                而非直线距离。距离计算基于道路网络的步行路径。
              </p>
            </div>
          </div>
        </div>

        <div class="grid gap-5 lg:grid-cols-2">
          <article
            v-for="(item, index) in facilityItems"
            :key="item.facility_id"
            class="group relative flex h-full flex-col gap-4 overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-md transition-all duration-300 hover:-translate-y-2 hover:shadow-xl"
          >
            <!-- 排名徽章 -->
            <div class="absolute left-4 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-sm font-black text-white shadow-lg">
              {{ index + 1 }}
            </div>
            
            <!-- 装饰性背景 -->
            <div class="absolute right-0 top-0 h-24 w-24 -translate-y-6 translate-x-6 rounded-full bg-gradient-to-br from-green-400/10 to-emerald-500/10 blur-2xl transition-transform group-hover:scale-150"></div>
            
            <header class="relative flex items-start justify-between gap-4 pl-12">
              <div class="flex-1">
                <h3 class="text-lg font-bold text-slate-900 transition group-hover:text-primary">
                  {{ item.name }}
                </h3>
                <p class="mt-1 text-xs text-slate-500">
                  <span class="font-medium">设施 ID: {{ item.facility_id }}</span>
                </p>
              </div>
              <span class="flex-shrink-0 rounded-xl bg-gradient-to-br from-emerald-50 to-green-50 px-3 py-2 text-xs font-bold text-emerald-700 shadow-sm">
                {{ FACILITY_CATEGORY_LABELS[item.category] ?? item.category }}
              </span>
            </header>

            <!-- 距离和时间 - 突出显示 -->
            <div class="relative">
              <div class="grid grid-cols-2 gap-4 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 p-5 border-2 border-blue-100">
                <div class="text-center">
                  <dt class="mb-2 flex items-center justify-center gap-1 text-xs font-semibold text-blue-600">
                    📍 路径距离
                  </dt>
                  <dd class="text-2xl font-black text-blue-900">
                    {{ item.distance.toFixed(1) }}
                    <span class="text-sm font-normal">米</span>
                  </dd>
                  <p class="mt-1 text-xs text-blue-600">实际步行距离</p>
                </div>
                <div class="text-center border-l-2 border-blue-200">
                  <dt class="mb-2 flex items-center justify-center gap-1 text-xs font-semibold text-emerald-600">
                    ⏱️ 预计耗时
                  </dt>
                  <dd class="text-2xl font-black text-emerald-900">
                    {{ item.travel_time.toFixed(1) }}
                    <span class="text-sm font-normal">分钟</span>
                  </dd>
                  <p class="mt-1 text-xs text-emerald-600">到达时间</p>
                </div>
              </div>
            </div>

            <!-- 路径信息 -->
            <div class="relative rounded-xl bg-slate-50 p-4 space-y-3">
              <div>
                <dt class="mb-2 flex items-center gap-1 text-xs font-semibold text-slate-600">
                  🛤️ 途经节点（共 {{ item.node_sequence.length }} 个）
                </dt>
                <dd class="flex flex-wrap gap-2">
                  <span
                    v-for="(nodeId, idx) in item.node_sequence"
                    :key="nodeId"
                    class="inline-flex items-center rounded-lg bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700"
                    :class="{ 'bg-emerald-100 text-emerald-700': idx === 0 || idx === item.node_sequence.length - 1 }"
                  >
                    <span v-if="idx === 0" class="mr-1">🚩</span>
                    <span v-else-if="idx === item.node_sequence.length - 1" class="mr-1">🎯</span>
                    #{{ nodeId }}
                  </span>
                </dd>
              </div>
            </div>

            <!-- 最近标记 -->
            <div v-if="index === 0" class="absolute bottom-4 right-4">
              <div class="rounded-full bg-gradient-to-r from-yellow-400 to-orange-400 px-3 py-1.5 text-xs font-bold text-white shadow-lg">
                ⭐ 最近
              </div>
            </div>
          </article>
        </div>
      </template>
      <template v-else>
        <EmptyState
          title="暂无查询结果"
          description="请调整筛选条件后再次尝试，或使用上方示例快速填充参数。"
          icon="🏙️"
        />
      </template>
    </PageSection>
  </div>
</template>
