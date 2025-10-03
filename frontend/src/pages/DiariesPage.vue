<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import PageSection from '../components/ui/PageSection.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import DiaryCard from '../components/diary/DiaryCard.vue'
import DiaryFilters from '../components/diary/DiaryFilters.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { fetchDiaryRecommendations, searchDiaries } from '../services/api'
import { useDiariesStore } from '../stores/diaries'
import type { DiaryListItem } from '../types/diary'

const diariesStore = useDiariesStore()
const router = useRouter()

// Determine if we're in search mode
const isSearchMode = computed(() => {
  return diariesStore.filters.fullTextSearch.trim() !== ''
})

// API request state for recommendations
const {
  data: recommendationsData,
  error: recommendationsError,
  loading: recommendationsLoading,
  execute: loadRecommendations,
} = useApiRequest(fetchDiaryRecommendations)

// API request state for search
const {
  data: searchData,
  error: searchError,
  loading: searchLoading,
  execute: loadSearch,
} = useApiRequest(searchDiaries)

// Computed properties for current data
const currentData = computed(() => {
  if (isSearchMode.value) {
    return searchData.value
  } else {
    // For recommendations, create a unified interface
    const recData = recommendationsData.value
    if (recData) {
      return {
        ...recData,
        total: recData.total_candidates, // Use total_candidates as total for consistency
      }
    }
    return null
  }
})

const error = computed(() => {
  return isSearchMode.value ? searchError.value : recommendationsError.value
})

const loading = computed(() => {
  return isSearchMode.value ? searchLoading.value : recommendationsLoading.value
})

// Unified diary items for template
const diaryItems = computed(() => {
  if (!currentData.value) return []
  return currentData.value.items.map(item => {
    if (isSearchMode.value) {
      // item is DiaryListItem
      return {
        diary: item as DiaryListItem,
        recommendationScore: undefined,
        showCompressionStatus: false,
        animationThumbnail: undefined,
      }
    } else {
      // item is DiaryRecommendationItem
      const recItem = item as any
      return {
        diary: recItem.diary as DiaryListItem,
        recommendationScore: recItem.score,
        showCompressionStatus: false, // Could be added to recommendation response
        animationThumbnail: undefined, // Could be added later
      }
    }
  })
})

// Load initial data
onMounted(async () => {
  await handleFiltersChanged()
})

// Handle filter changes
const handleFiltersChanged = async () => {
  if (isSearchMode.value) {
    await loadSearch(diariesStore.filters.fullTextSearch, {
      limit: 20,
      sort_by: diariesStore.filters.sortBy,
      interests: diariesStore.filters.interests,
      region_id: diariesStore.filters.regionId || undefined,
    })
  } else {
    await loadRecommendations({
      limit: 20,
      sort_by: diariesStore.filters.sortBy,
      interests: diariesStore.filters.interests,
      region_id: diariesStore.filters.regionId || undefined,
    })
  }
}

// Handle diary card click
const handleDiaryClick = (diary: DiaryListItem) => {
  void router.push({ name: 'diary-detail', params: { id: diary.id } })
}

// Handle create diary button
const handleCreateDiary = () => {
  void router.push({ name: 'diary-create' })
}
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="旅游日记"
      description="浏览和分享旅游体验，发现精彩的旅行故事"
    >
      <!-- Action Buttons -->
      <div class="mb-6 flex justify-end gap-3">
        <button
          class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
          @click="handleCreateDiary"
        >
          ✏️ 撰写日记
        </button>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <!-- Filters Sidebar -->
        <div class="lg:col-span-1">
          <DiaryFilters
            @update:sort-by="diariesStore.setSortBy"
            @update:interests="diariesStore.setInterests"
            @update:region-id="diariesStore.setRegionId"
            @update:search="diariesStore.setSearch"
            @update:full-text-search="diariesStore.setSearch"
            @filters-changed="handleFiltersChanged"
          />
        </div>

        <!-- Diary List -->
        <div class="lg:col-span-3">
          <!-- Loading State -->
          <LoadingIndicator v-if="loading" message="加载日记中..." />

          <!-- Error State -->
          <ErrorAlert v-else-if="error" :message="error.message" />

          <!-- Empty State -->
          <EmptyState
            v-else-if="!currentData || currentData.items.length === 0"
            :icon="isSearchMode ? '�' : '�📝'"
            :title="isSearchMode ? '未找到相关日记' : '暂无日记'"
            :message="isSearchMode ? '试试调整搜索关键词或筛选条件' : '还没有符合条件的旅游日记，试试调整筛选条件吧'"
          />

          <!-- Diary Grid -->
          <div v-else class="space-y-4">
            <!-- Results Summary -->
            <div class="flex items-center justify-between text-sm text-slate-600">
              <span>找到 {{ currentData.total }} 篇日记</span>
              <span class="text-slate-400">
                排序方式：
                {{
                  {
                    hybrid: '综合推荐',
                    popularity: '热度优先',
                    rating: '评分优先',
                    latest: '最新发布',
                  }[diariesStore.filters.sortBy]
                }}
              </span>
            </div>

            <!-- Diary Cards Grid -->
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <DiaryCard
                v-for="item in diaryItems"
                :key="item.diary.id"
                :diary="item.diary"
                :show-compression-status="item.showCompressionStatus"
                :recommendation-score="item.recommendationScore"
                :animation-thumbnail="item.animationThumbnail"
                @click="handleDiaryClick"
              />
            </div>

            <!-- Pagination Placeholder -->
            <div class="mt-6 flex justify-center">
              <div class="text-sm text-slate-400">
                <!-- TODO: Add pagination component -->
                分页功能待实现
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageSection>
  </div>
</template>