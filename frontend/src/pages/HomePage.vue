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
      title="旅游目的地推荐"
      description="按照旅游热度、评价和个人兴趣选择旅游目的地，支持关键词查询和多维度排序。"
    >
      <form class="rounded-2xl border border-slate-200 bg-white p-6 shadow-lg" @submit.prevent="runQuery">
        <div class="grid gap-5 md:grid-cols-2">
          <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
            <span class="flex items-center gap-2">
              🔍 搜索关键词
            </span>
            <input
              v-model="form.search"
              type="text"
              placeholder="输入城市、景点或关键字"
              class="rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary"
            />
          </label>

          <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
            <span class="flex items-center gap-2">
              📊 推荐数量
            </span>
            <input 
              v-model.number="form.limit" 
              type="number" 
              min="1" 
              max="50" 
              class="rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary"
            />
          </label>

          <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
            <span class="flex items-center gap-2">
              📈 排序方式
            </span>
            <select v-model="form.sortBy" class="rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary">
              <option v-for="option in sortOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="flex flex-col gap-2 text-sm font-semibold text-slate-700">
            <span class="flex items-center gap-2">
              🏷️ 区域类型
            </span>
            <select v-model="form.regionType" class="rounded-xl border-2 border-slate-200 px-4 py-2.5 transition focus:border-primary">
              <option v-for="option in regionTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <div class="flex flex-col gap-3 md:col-span-2">
            <label class="text-sm font-semibold text-slate-700">
              <span class="flex items-center gap-2">
                💡 兴趣标签
              </span>
            </label>
            <textarea
              v-model="form.interestsText"
              rows="2"
              placeholder="以逗号、空格或换行分隔，例如：美食、自然、文化"
              class="rounded-xl border-2 border-slate-200 px-4 py-3 transition focus:border-primary"
            />
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs font-medium text-slate-500">快捷选择：</span>
              <button
                v-for="interest in INTEREST_SUGGESTIONS"
                :key="interest"
                type="button"
                class="rounded-full border-2 px-3 py-1.5 text-xs font-medium transition-all"
                :class="
                  interestList.includes(interest)
                    ? 'border-primary bg-primary text-white shadow-md shadow-primary/30'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-primary hover:text-primary'
                "
                @click="toggleInterest(interest)"
              >
                {{ interest }}
              </button>
            </div>
          </div>

          <label class="flex items-center gap-3 text-sm font-semibold text-slate-700 md:col-span-2">
            <input v-model="form.interestsOnly" type="checkbox" class="h-5 w-5 rounded border-2 border-slate-300 text-primary focus:ring-2 focus:ring-primary/30" />
            <span>只显示匹配兴趣的区域</span>
          </label>

          <div class="flex flex-col gap-3 rounded-xl bg-slate-50 p-4 md:col-span-2">
            <span class="text-xs font-semibold text-slate-600">⚡ 快速示例</span>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="sample in SAMPLE_REGION_OPTIONS"
                :key="sample.id"
                type="button"
                class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm transition hover:border-primary hover:text-primary hover:shadow"
                @click="applyRegionSample(sample.id)"
              >
                {{ sample.name }} · {{ sample.type === 'scenic' ? '🏞️' : '🏫' }} · #{{ sample.id }}
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5 md:col-span-2">
            <button
              type="submit"
              class="rounded-xl bg-gradient-to-r from-primary to-blue-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-primary/30 transition hover:shadow-xl hover:shadow-primary/40 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none"
              :disabled="loading"
            >
              {{ loading ? '🔄 加载中…' : '🚀 获取推荐' }}
            </button>
            <button
              type="button"
              class="rounded-xl border-2 border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-600 transition hover:border-primary hover:text-primary"
              @click="resetFilters"
            >
              🔄 重置条件
            </button>
            <span v-if="hasActiveFilters" class="text-xs font-medium text-slate-500">
              ✓ 已应用筛选条件
            </span>
          </div>
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

        <div class="grid gap-5 lg:grid-cols-2">
          <article
            v-for="item in sortedItems"
            :key="item.region.id"
            class="group relative flex h-full flex-col justify-between overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-md transition-all duration-300 hover:-translate-y-2 hover:shadow-xl"
          >
            <!-- 装饰性渐变背景 -->
            <div class="absolute right-0 top-0 h-32 w-32 -translate-y-8 translate-x-8 rounded-full bg-gradient-to-br from-primary/5 to-blue-500/10 blur-3xl transition-transform group-hover:scale-150"></div>
            
            <div class="relative space-y-4">
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1">
                  <h3 class="text-xl font-bold text-slate-900 transition group-hover:text-primary">
                    {{ item.region.name }}
                  </h3>
                  <p class="mt-1 text-xs text-slate-500">
                    <span class="font-medium">ID: {{ item.region.id }}</span>
                    <span class="mx-2">·</span>
                    <span>{{ item.region.city ?? '未知城市' }}</span>
                  </p>
                </div>
                <span class="flex-shrink-0 rounded-xl bg-gradient-to-br from-primary/10 to-blue-500/10 px-4 py-2 text-xs font-bold text-primary shadow-sm">
                  {{ item.region.type === 'scenic' ? '🏞️ 景区' : '🏫 校园' }}
                </span>
              </div>

              <div class="flex items-center gap-4 text-sm">
                <div class="flex items-center gap-1.5">
                  <span class="text-yellow-500">⭐</span>
                  <span class="font-semibold text-slate-700">{{ item.region.rating.toFixed(1) }}</span>
                  <span class="text-slate-400">评分</span>
                </div>
                <div class="h-4 w-px bg-slate-200"></div>
                <div class="flex items-center gap-1.5">
                  <span class="text-red-500">🔥</span>
                  <span class="font-semibold text-slate-700">{{ item.region.popularity }}</span>
                  <span class="text-slate-400">人气</span>
                </div>
              </div>

              <p v-if="item.region.description" class="text-sm leading-relaxed text-slate-600">
                {{ item.region.description.length > 100 ? item.region.description.slice(0, 100) + '...' : item.region.description }}
              </p>
            </div>

            <div class="relative mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
              <span class="rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
                匹配度 {{ item.score.toFixed(2) }}
              </span>
              <span class="rounded-lg bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600">
                基础分 {{ item.base_score.toFixed(2) }}
              </span>
              <template v-if="item.interest_matches.length">
                <span v-for="tag in item.interest_matches" :key="tag" class="rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                  ✓ {{ tag }}
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
