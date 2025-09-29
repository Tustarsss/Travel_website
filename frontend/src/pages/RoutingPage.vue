<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { fetchRoutePlan } from '../services/api'
import type { RoutePlanResponse, TransportMode, WeightStrategy } from '../types/api'
import { SAMPLE_ROUTING_COMBINATIONS, TRANSPORT_MODE_LABELS } from '../constants/demoOptions'
import { usePreferencesStore, createRoutingDefaults } from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

interface RoutingFormState {
  regionId: number
  startNodeId: number
  endNodeId: number
  strategy: WeightStrategy
  transportModes: TransportMode[]
}

const weightStrategyOptions: { label: string; value: WeightStrategy }[] = [
  { label: '耗时最短', value: 'time' },
  { label: '距离最短', value: 'distance' },
]

const transportModeOptions = Object.entries(TRANSPORT_MODE_LABELS).map(([value, label]) => ({
  value: value as TransportMode,
  label,
}))

const preferencesStore = usePreferencesStore()
const { routing } = storeToRefs(preferencesStore)

const form = reactive<RoutingFormState>({
  regionId: 1,
  startNodeId: 1,
  endNodeId: 2,
  strategy: 'time',
  transportModes: [],
})

const hydrateForm = (prefs = routing.value) => {
  form.regionId = prefs.regionId
  form.startNodeId = prefs.startNodeId
  form.endNodeId = prefs.endNodeId
  form.strategy = prefs.strategy
  form.transportModes = [...prefs.transportModes]
}

watch(
  routing,
  (value) => {
    hydrateForm(value)
  },
  { immediate: true }
)

const { data, error, loading, execute } = useApiRequest(fetchRoutePlan)

const submit = async () => {
  const payload = {
    regionId: form.regionId,
    startNodeId: form.startNodeId,
    endNodeId: form.endNodeId,
    strategy: form.strategy,
    transportModes: form.transportModes,
  }

  await execute(payload)
  preferencesStore.updateRouting({ ...payload })
}

const applySample = (index: number) => {
  const sample = SAMPLE_ROUTING_COMBINATIONS[index]
  if (!sample) return
  form.regionId = sample.regionId
  form.startNodeId = sample.startNodeId
  form.endNodeId = sample.endNodeId
}

const resetRouting = () => {
  const defaults = createRoutingDefaults()
  preferencesStore.updateRouting(defaults)
  hydrateForm(defaults)
}

const plan = computed<RoutePlanResponse | null>(() => data.value ?? null)

const allowedModes = computed(() => plan.value?.allowed_transport_modes ?? [])
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="路线规划"
      description="输入图节点信息即可获取最优路线，支持按时间或距离进行优化，并可限定交通方式。"
    >
      <form class="grid gap-4 md:grid-cols-2" @submit.prevent="submit">
        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          区域 ID
          <input v-model.number="form.regionId" type="number" min="1" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          起点节点 ID
          <input v-model.number="form.startNodeId" type="number" min="1" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          终点节点 ID
          <input v-model.number="form.endNodeId" type="number" min="1" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          优化策略
          <select v-model="form.strategy">
            <option v-for="option in weightStrategyOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <fieldset class="col-span-full flex flex-col gap-2">
          <legend class="text-sm font-medium text-slate-600">限定交通方式（可选）</legend>
          <div class="flex flex-wrap gap-4 text-sm text-slate-600">
            <label v-for="option in transportModeOptions" :key="option.value" class="inline-flex items-center gap-2">
              <input v-model="form.transportModes" type="checkbox" :value="option.value" class="h-4 w-4" />
              {{ option.label }}
            </label>
          </div>
          <p class="text-xs text-slate-400">不选择则默认使用后端允许的全部交通方式。</p>
        </fieldset>

        <div class="flex flex-col gap-2 text-xs text-slate-500 md:col-span-2">
          <span class="font-medium text-slate-600">快速示例</span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(sample, index) in SAMPLE_ROUTING_COMBINATIONS"
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
            {{ loading ? '规划中…' : '计算路线' }}
          </button>
          <button
            type="button"
            class="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-primary/50 hover:text-primary"
            @click="resetRouting"
          >
            重置参数
          </button>
        </div>
      </form>
    </PageSection>

    <PageSection title="路线详情" description="当找到有效路径时，将展示节点顺序、路段信息及总距离/时间。">
      <template v-if="error">
        <ErrorAlert :message="error.message" />
      </template>
      <template v-else-if="loading">
        <LoadingIndicator label="正在计算最优路线，请稍候…" />
      </template>
      <template v-else-if="plan">
        <div class="flex flex-col gap-3 text-xs text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>
            更新时间：
            <span class="font-medium text-slate-700">
              {{ plan.generated_at ? new Date(plan.generated_at).toLocaleString() : '—' }}
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-slate-400">允许交通方式：</span>
            <span
              v-for="mode in allowedModes"
              :key="mode"
              class="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600"
            >
              {{ TRANSPORT_MODE_LABELS[mode as TransportMode] ?? mode }}
            </span>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-3">
          <div class="rounded-xl border border-slate-200 bg-white/80 p-4 text-center">
            <p class="text-xs text-slate-400">总距离</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ plan.total_distance.toFixed(2) }} km</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white/80 p-4 text-center">
            <p class="text-xs text-slate-400">总耗时</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ plan.total_time.toFixed(2) }} min</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white/80 p-4 text-center">
            <p class="text-xs text-slate-400">区域 ID</p>
            <p class="mt-1 text-lg font-semibold text-slate-900">{{ plan.region_id }}</p>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
            <h3 class="text-lg font-semibold text-slate-900">节点序列</h3>
            <ol class="mt-4 space-y-2 text-sm text-slate-600">
              <li v-for="(node, index) in plan.nodes" :key="node.id" class="flex items-center gap-3">
                <span class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {{ index + 1 }}
                </span>
                <div class="flex flex-col">
                  <span class="font-medium text-slate-800">{{ node.name ?? `节点 ${node.id}` }}</span>
                  <span class="text-xs text-slate-400">({{ node.latitude.toFixed(6) }}, {{ node.longitude.toFixed(6) }})</span>
                </div>
              </li>
            </ol>
          </div>

          <div class="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
            <h3 class="text-lg font-semibold text-slate-900">路段详情</h3>
            <ul class="mt-4 space-y-3 text-sm text-slate-600">
              <li
                v-for="segment in plan.segments"
                :key="`${segment.source_id}-${segment.target_id}-${segment.transport_mode}`"
                class="rounded-lg border border-slate-200 bg-white/60 p-3"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <span class="font-medium text-slate-800">{{ segment.source_id }} → {{ segment.target_id }}</span>
                  <span class="rounded bg-slate-100 px-2 py-1 text-xs">
                    {{ TRANSPORT_MODE_LABELS[segment.transport_mode as TransportMode] ?? segment.transport_mode }}
                  </span>
                </div>
                <div class="mt-2 flex gap-4 text-xs text-slate-500">
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
          description="请调整参数后重试，或从上方示例快速填充节点信息。"
          icon="🛣️"
        />
      </template>
    </PageSection>
  </div>
</template>
