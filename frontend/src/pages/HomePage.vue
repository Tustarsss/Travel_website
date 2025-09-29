<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { fetchRegionRecommendations } from '../services/api'
import type { RecommendationSort, RegionRecommendationItem, RegionType } from '../types/api'
import { INTEREST_SUGGESTIONS, SAMPLE_REGION_OPTIONS } from '../constants/demoOptions'
import { usePreferencesStore, createRecommendationDefaults } from '../stores/preferences'
import { useApiRequest } from '../composables/useApiRequest'

interface RecommendationForm {
  search: string
  interestsText: string
  limit: number
  sortBy: RecommendationSort
  regionType: RegionType | ''
  interestsOnly: boolean
}

const sortOptions: { label: string; value: RecommendationSort }[] = [
  { label: '综合评分优先', value: 'hybrid' },
  { label: '人气优先', value: 'popularity' },
  { label: '评分优先', value: 'rating' },
]

const regionTypeOptions: { label: string; value: RegionType | '' }[] = [
  { label: '不限类型', value: '' },
  { label: '景区 (scenic)', value: 'scenic' },
  { label: '校园 (campus)', value: 'campus' },
]

const preferencesStore = usePreferencesStore()
const { recommendation } = storeToRefs(preferencesStore)

const form = reactive<RecommendationForm>({
  search: '',
  interestsText: '',
  limit: 10,
  sortBy: 'hybrid',
  regionType: '',
  interestsOnly: false,
})

const hydrateForm = (prefs = recommendation.value) => {
  form.search = prefs.search
  form.limit = prefs.limit
  form.sortBy = prefs.sortBy
  form.regionType = prefs.regionType
  form.interestsOnly = prefs.interestsOnly
  form.interestsText = prefs.interests.join('、')
}

watch(
  recommendation,
  (value) => {
    hydrateForm(value)
  },
  { immediate: true }
)

const interestList = computed(() =>
  form.interestsText
    .split(/[,，;；\s\n]+/u)
    .map((item) => item.trim())
    .filter(Boolean)
)

const defaultPrefs = createRecommendationDefaults()

const hasActiveFilters = computed(() =>
  Boolean(
    form.search ||
      form.regionType ||
      form.interestsOnly ||
      interestList.value.length > 0 ||
      form.limit !== defaultPrefs.limit ||
      form.sortBy !== defaultPrefs.sortBy
  )
)

const { data, error, loading, execute } = useApiRequest(fetchRegionRecommendations)

const runQuery = async () => {
  const payload = {
    limit: form.limit,
    sortBy: form.sortBy,
    search: form.search || undefined,
    regionType: form.regionType || undefined,
    interestsOnly: form.interestsOnly,
    interests: interestList.value,
  }

  await execute(payload)
  preferencesStore.updateRecommendation({
    limit: form.limit,
    sortBy: form.sortBy,
    search: form.search,
    regionType: form.regionType,
    interestsOnly: form.interestsOnly,
    interests: interestList.value,
  })
}

const toggleInterest = (interest: string) => {
  const set = new Set(interestList.value)
  if (set.has(interest)) {
    set.delete(interest)
  } else {
    set.add(interest)
  }
  form.interestsText = Array.from(set).join('、')
}

const applyRegionSample = (regionId: number) => {
  const sample = SAMPLE_REGION_OPTIONS.find((item) => item.id === regionId)
  if (!sample) return
  form.search = sample.name
  form.regionType = sample.type as RegionType
}

const resetFilters = () => {
  const defaults = createRecommendationDefaults()
  preferencesStore.updateRecommendation(defaults)
  hydrateForm(defaults)
}

const sortedItems = computed<RegionRecommendationItem[]>(() => data.value?.items ?? [])
const generatedAt = computed(() => data.value?.generated_at ?? null)
const totalCount = computed(() => data.value?.total_candidates ?? 0)
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="智能区域推荐"
      description="根据兴趣标签、搜索关键词和区域类型自动生成个性化目的地列表。"
    >
      <form class="grid gap-4 md:grid-cols-2" @submit.prevent="runQuery">
        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          搜索关键词
          <input
            v-model="form.search"
            type="text"
            placeholder="输入城市、景点或关键字"
          />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          推荐数量
          <input v-model.number="form.limit" type="number" min="1" max="50" />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          排序方式
          <select v-model="form.sortBy">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600">
          区域类型
          <select v-model="form.regionType">
            <option v-for="option in regionTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium text-slate-600 md:col-span-2">
          兴趣标签
          <textarea
            v-model="form.interestsText"
            rows="2"
            placeholder="以逗号、空格或换行分隔，例如：美食、自然、文化"
          />
          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>快捷选择：</span>
            <button
              v-for="interest in INTEREST_SUGGESTIONS"
              :key="interest"
              type="button"
              class="rounded-full border px-3 py-1"
              :class="
                interestList.includes(interest)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-primary/60 hover:text-primary'
              "
              @click="toggleInterest(interest)"
            >
              {{ interest }}
            </button>
          </div>
        </label>

        <label class="flex items-center gap-3 text-sm font-medium text-slate-600">
          <input v-model="form.interestsOnly" type="checkbox" class="h-4 w-4" />
          只显示匹配兴趣的区域
        </label>

        <div class="flex flex-col gap-2 text-xs text-slate-500 md:col-span-2">
          <span class="font-medium text-slate-600">快速示例</span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="sample in SAMPLE_REGION_OPTIONS"
              :key="sample.id"
              type="button"
              class="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-600 hover:border-primary/60 hover:text-primary"
              @click="applyRegionSample(sample.id)"
            >
              {{ sample.name }} · {{ sample.type === 'scenic' ? '景区' : '校园' }} · #{{ sample.id }}
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3 md:col-span-2">
          <button
            type="submit"
            class="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-primary/90"
            :disabled="loading"
          >
            {{ loading ? '加载中…' : '获取推荐' }}
          </button>
          <button
            type="button"
            class="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-primary/50 hover:text-primary"
            @click="resetFilters"
          >
            重置条件
          </button>
          <span v-if="hasActiveFilters" class="text-xs text-slate-400">已应用筛选条件，可点击重置恢复默认。</span>
        </div>
      </form>
    </PageSection>

    <PageSection
      title="推荐结果"
      :description="
        data
          ? `共 ${data.total_candidates} 条候选，按 ${
              form.sortBy === 'hybrid' ? '综合评分' : form.sortBy === 'popularity' ? '人气' : '评分'
            } 排序。`
          : '提交条件后即可查看候选结果。'
      "
    >
      <template v-if="error">
        <ErrorAlert :message="error.message" />
      </template>
      <template v-else-if="loading">
        <LoadingIndicator label="正在加载推荐列表，请稍候…" />
      </template>
      <template v-else-if="sortedItems.length">
        <div class="flex flex-col gap-3 text-xs text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>
            请求上次更新时间：
            <span class="font-medium text-slate-700">
              {{ generatedAt ? new Date(generatedAt).toLocaleString() : '—' }}
            </span>
          </div>
          <div>返回数量：{{ sortedItems.length }} / {{ totalCount }}</div>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <article
            v-for="item in sortedItems"
            :key="item.region.id"
            class="flex h-full flex-col justify-between rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-semibold text-slate-900">{{ item.region.name }}</h3>
                  <p class="text-xs text-slate-400">ID：{{ item.region.id }} · {{ item.region.city ?? '未知城市' }}</p>
                </div>
                <span class="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  {{ item.region.type === 'scenic' ? '景区' : '校园' }}
                </span>
              </div>
              <p class="text-sm text-slate-600">
                评分 {{ item.region.rating.toFixed(1) }} · 人气 {{ item.region.popularity }}
              </p>
              <p v-if="item.region.description" class="text-sm text-slate-500 leading-relaxed">
                {{ item.region.description }}
              </p>
            </div>

            <div class="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span class="rounded-full bg-slate-100 px-2 py-1">匹配度 {{ item.score.toFixed(2) }}</span>
              <span class="rounded-full bg-slate-100 px-2 py-1">基础分 {{ item.base_score.toFixed(2) }}</span>
              <template v-if="item.interest_matches.length">
                <span v-for="tag in item.interest_matches" :key="tag" class="rounded-full bg-emerald-100 px-2 py-1 text-emerald-600">
                  匹配 {{ tag }}
                </span>
              </template>
            </div>
          </article>
        </div>
      </template>
      <template v-else>
        <EmptyState
          title="暂无推荐结果"
          description="请调整筛选条件后再次尝试，或使用上方示例快速填充参数。"
          icon="🧭"
        />
      </template>
    </PageSection>
  </div>
</template>
