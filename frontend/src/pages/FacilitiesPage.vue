<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { fetchNearbyFacilities } from '../services/api'
import type {
  FacilityCategory,
  FacilityRouteItem,
  FacilityRouteResponse,
  TransportMode,
  WeightStrategy,
} from '../types/api'
import {
  FACILITY_CATEGORY_LABELS,
  SAMPLE_FACILITY_QUERIES,
  TRANSPORT_MODE_LABELS,
} from '../constants/demoOptions'
import { usePreferencesStore, createFacilityDefaults } from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

interface FacilityFormState {
  regionId: number
  originNodeId: number
  radiusMeters: number | null
  limit: number
  strategy: WeightStrategy
  categories: FacilityCategory[]
  transportModes: TransportMode[]
}

const strategyOptions: { label: string; value: WeightStrategy }[] = [
  { label: '距离优先', value: 'distance' },
  { label: '时间优先', value: 'time' },
]

const preferencesStore = usePreferencesStore()
const { facilities } = storeToRefs(preferencesStore)

const form = reactive<FacilityFormState>({
  regionId: 1,
  originNodeId: 1,
  radiusMeters: 500,
  limit: 10,
  strategy: 'distance',
  categories: [],
  transportModes: [],
})

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

const buildPayload = () => ({
  regionId: form.regionId,
  originNodeId: form.originNodeId,
  radiusMeters: form.radiusMeters ?? undefined,
  limit: form.limit,
  strategy: form.strategy,
  categories: form.categories,
  transportModes: form.transportModes,
})

const { data, error, loading, execute } = useApiRequest(fetchNearbyFacilities)

const hydrateForm = (prefs = facilities.value) => {
  form.regionId = prefs.regionId
  form.originNodeId = prefs.originNodeId
  form.radiusMeters = prefs.radiusMeters
  form.limit = prefs.limit
  form.strategy = prefs.strategy
  form.categories = [...prefs.categories]
  form.transportModes = [...prefs.transportModes]
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
    limit: form.limit,
    strategy: form.strategy,
    categories: [...form.categories],
    transportModes: [...form.transportModes],
  })
}

const applySample = (index: number) => {
  const sample = SAMPLE_FACILITY_QUERIES[index]
  if (!sample) return
  form.regionId = sample.regionId
  form.originNodeId = sample.originNodeId
  form.radiusMeters = sample.radius
}

const resetFilters = () => {
  const defaults = createFacilityDefaults()
  preferencesStore.updateFacilities(defaults)
  hydrateForm(defaults)
}

const results = computed<FacilityRouteResponse | null>(() => data.value ?? null)
const facilityItems = computed<FacilityRouteItem[]>(() => results.value?.items ?? [])
const totalFacilities = computed(() => results.value?.total ?? 0)
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="设施查询"
      description="根据出发节点与搜索半径检索附近设施，可按类别及交通方式过滤，并生成最优路线信息。"
    >
      <form class="grid gap-4 md:grid-cols-2" @submit.prevent="runQuery">
        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          区域 ID
          <input v-model.number="form.regionId" type="number" min="1" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          出发节点 ID
          <input v-model.number="form.originNodeId" type="number" min="1" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          搜索半径（米）
          <input v-model.number="form.radiusMeters" type="number" min="0" />
          <span class="text-xs font-normal text-slate-400">留空表示由后端采用默认半径。</span>
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          返回数量
          <input v-model.number="form.limit" type="number" min="1" max="50" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          优化策略
          <select v-model="form.strategy">
            <option v-for="option in strategyOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <fieldset class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          <legend>设施类别（多选）</legend>
          <div class="grid grid-cols-2 gap-3 text-sm text-slate-600 md:grid-cols-3">
            <label v-for="option in facilityCategoryOptions" :key="option.value" class="inline-flex items-center gap-2">
              <input v-model="form.categories" type="checkbox" :value="option.value" class="h-4 w-4" />
              {{ option.label }}
            </label>
          </div>
          <p class="text-xs text-slate-400">不选择则默认返回所有类别。</p>
        </fieldset>

        <fieldset class="col-span-full flex flex-col gap-2 text-sm font-medium text-slate-600">
          <legend>交通方式（可选）</legend>
          <div class="flex flex-wrap gap-4 text-sm text-slate-600">
            <label v-for="option in transportModeOptions" :key="option.value" class="inline-flex items-center gap-2">
              <input v-model="form.transportModes" type="checkbox" :value="option.value" class="h-4 w-4" />
              {{ option.label }}
            </label>
          </div>
        </fieldset>

        <div class="flex flex-col gap-2 text-xs text-slate-500 md:col-span-2">
          <span class="font-medium text-slate-600">快速示例</span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(sample, index) in SAMPLE_FACILITY_QUERIES"
              :key="sample.label"
              type="button"
              class="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-600 hover:border-primary/60 hover:text-primary"
              @click="applySample(index)"
            >
              {{ sample.label }}
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3 md:col-span-2">
          <button
            type="submit"
            class="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-primary/90"
            :disabled="loading"
          >
            {{ loading ? '搜索中…' : '查询设施' }}
          </button>
          <button
            type="button"
            class="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-primary/50 hover:text-primary"
            @click="resetFilters"
          >
            重置条件
          </button>
        </div>
      </form>
    </PageSection>

    <PageSection
      title="查询结果"
      :description="
        results
          ? `共找到 ${totalFacilities} 个设施，列出最优路线距离与耗时。`
          : '提交条件后即可查看附近设施及路线信息。'
      "
    >
      <template v-if="error">
        <ErrorAlert :message="error.message" />
      </template>
      <template v-else-if="loading">
        <LoadingIndicator label="正在检索附近设施，请稍候…" />
      </template>
      <template v-else-if="facilityItems.length">
        <div class="flex flex-col gap-3 text-xs text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>
            区域 ID：<span class="font-medium text-slate-700">{{ results?.region_id }}</span>
            · 起点节点：<span class="font-medium text-slate-700">{{ results?.origin_node_id }}</span>
          </div>
          <div>
            搜索半径：
            <span class="font-medium text-slate-700">
              {{ results?.radius_meters ? `${results?.radius_meters} m` : '后端默认' }}
            </span>
          </div>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <article
            v-for="item in facilityItems"
            :key="item.facility_id"
            class="flex h-full flex-col gap-3 rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <header class="flex items-start justify-between gap-4">
              <div>
                <h3 class="text-lg font-semibold text-slate-900">{{ item.name }}</h3>
                <p class="text-xs text-slate-400">设施 ID：{{ item.facility_id }}</p>
              </div>
              <span class="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                {{ FACILITY_CATEGORY_LABELS[item.category] ?? item.category }}
              </span>
            </header>

            <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-slate-600">
              <div>
                <dt class="text-xs text-slate-400">距离</dt>
                <dd class="font-medium text-slate-800">{{ item.distance.toFixed(2) }} m</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400">预计耗时</dt>
                <dd class="font-medium text-slate-800">{{ item.travel_time.toFixed(2) }} min</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400">规划策略</dt>
                <dd class="font-medium text-slate-800">
                  {{ item.strategy === 'distance' ? '距离优先' : '时间优先' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400">交通方式</dt>
                <dd class="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span
                    v-for="mode in form.transportModes.length ? form.transportModes : Object.keys(TRANSPORT_MODE_LABELS)"
                    :key="mode"
                    class="inline-flex items-center rounded bg-slate-100 px-2 py-1"
                  >
                    {{ TRANSPORT_MODE_LABELS[mode as TransportMode] ?? mode }}
                  </span>
                </dd>
              </div>
              <div class="col-span-2">
                <dt class="text-xs text-slate-400">节点序列</dt>
                <dd class="mt-1 flex flex-wrap gap-2 text-xs">
                  <span
                    v-for="nodeId in item.node_sequence"
                    :key="nodeId"
                    class="inline-flex items-center rounded bg-slate-100 px-2 py-1"
                  >
                    #{{ nodeId }}
                  </span>
                </dd>
              </div>
            </dl>
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
