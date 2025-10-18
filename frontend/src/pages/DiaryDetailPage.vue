<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageSection from '../components/ui/PageSection.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { fetchDiaryDetail, rateDiary, fetchDiaryRatings, recordDiaryView } from '../services/api'
import type { DiaryRatingRequest, DiaryRatingListResponse } from '../types/diary'

const route = useRoute()

// Get diary ID from route
const diaryId = ref<number>(parseInt(route.params.id as string))

// API request state
const {
  data: diary,
  error,
  loading,
  execute: loadDiary,
} = useApiRequest(fetchDiaryDetail)

// Rating state
const userRating = ref<number>(0)
const ratingComment = ref('')
const isSubmittingRating = ref(false)
const ratingData = ref<DiaryRatingListResponse | null>(null)
const ratingsPage = ref(1)
const ratingsPageSize = 5
const isLoadingRatings = ref(false)

const ratingItems = computed(() => ratingData.value?.items ?? [])
const averageScore = computed(() => ratingData.value?.average_score ?? 0)
const ratingDistribution = computed(() => {
  return [5, 4, 3, 2, 1].map((score) => {
    const count = ratingData.value?.score_distribution?.[score] ?? 0
    const total = ratingData.value?.total ?? 0
    const percentage = total > 0 ? Math.round((count / total) * 100) : 0
    return {
      score,
      count,
      percentage,
    }
  })
})
const ratingsTotal = computed(() => ratingData.value?.total ?? 0)
const commentsCount = computed(() => ratingData.value?.comments_count ?? 0)
const totalRatingPages = computed(() =>
  ratingData.value ? Math.max(1, Math.ceil(ratingData.value.total / ratingsPageSize)) : 1
)
const hasRatings = computed(() => ratingItems.value.length > 0)

// Load diary on mount
onMounted(async () => {
  if (diaryId.value) {
    try {
      await recordDiaryView(diaryId.value)
    } catch (error) {
      console.warn('Failed to record diary view:', error)
    }
    await loadDiary(diaryId.value)
    await loadRatings()
  }
})

const loadRatings = async (page: number = 1) => {
  if (!diaryId.value) return

  try {
    isLoadingRatings.value = true
    const data = await fetchDiaryRatings(diaryId.value, {
      page,
      page_size: ratingsPageSize,
    })

    ratingData.value = data
    ratingsPage.value = data.page

    if (data.current_user_rating) {
      userRating.value = data.current_user_rating.score
      ratingComment.value = data.current_user_rating.comment ?? ''
    } else {
      userRating.value = 0
      ratingComment.value = ''
    }
  } catch (error) {
    console.error('Failed to load ratings:', error)
  } finally {
    isLoadingRatings.value = false
  }
}

const goToRatingsPage = async (page: number) => {
  const totalPages = totalRatingPages.value
  const targetPage = Math.min(Math.max(page, 1), totalPages)
  if (targetPage === ratingsPage.value) return
  await loadRatings(targetPage)
}

// Handle rating submission
const submitRating = async () => {
  if (!diary.value || isSubmittingRating.value) return

  try {
    isSubmittingRating.value = true

    const ratingRequest: DiaryRatingRequest = {
      score: userRating.value,
      comment: ratingComment.value.trim() || undefined,
    }

    await rateDiary(diary.value.id, ratingRequest)

    // Refresh diary data to get updated ratings
    await loadDiary(diaryId.value)
    await loadRatings(1)
    ratingsPage.value = 1

    const currentRating = ratingData.value?.current_user_rating
    ratingComment.value = currentRating?.comment ?? ''

  } catch (error) {
    console.error('Failed to submit rating:', error)
  } finally {
    isSubmittingRating.value = false
  }
}

// Format date
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Format rating stars
const formatRating = (rating: number): string => {
  return '⭐'.repeat(Math.floor(rating)) + (rating % 1 >= 0.5 ? '⭐' : '')
}

const renderStars = (score: number): string => {
  const filled = '★'.repeat(score)
  const empty = '☆'.repeat(Math.max(0, 5 - score))
  return `${filled}${empty}`
}
</script>

<template>
  <div class="h-full">
    <LoadingIndicator v-if="loading" message="加载日记详情..." />
    <ErrorAlert v-else-if="error" :message="error.message" />
    <EmptyState
      v-else-if="!diary"
      icon="📝"
      title="日记不存在"
      message="找不到这篇日记，可能已被删除或不存在。"
    />

    <div
      v-else
      class="flex flex-col gap-6 md:h-[calc(100vh-8rem)] md:flex-row"
    >
      <div
        class="flex-1 space-y-6 md:overflow-y-auto md:pr-6"
      >
  <PageSection :title="diary.title" :description="`由 ${diary.author.username} 发布`">
          <div class="mb-4 flex flex-wrap items-center gap-4 text-sm text-slate-600">
            <div class="flex items-center gap-1">
              <span>📍</span>
              <span>{{ diary.region.name }}</span>
            </div>
            <div class="flex items-center gap-1">
              <span>👁️</span>
              <span>{{ diary.popularity }}</span>
            </div>
            <div class="flex items-center gap-1">
              <span>{{ formatRating(diary.rating) }}</span>
              <span>{{ diary.rating.toFixed(1) }} ({{ diary.ratings_count }}人评价)</span>
            </div>
            <div class="flex items-center gap-1">
              <span>📅</span>
              <span>{{ formatDate(diary.created_at) }}</span>
            </div>
          </div>

          <div v-if="diary.tags && diary.tags.length > 0" class="mb-4 flex flex-wrap gap-2">
            <span
              v-for="tag in diary.tags"
              :key="tag"
              class="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary"
            >
              #{{ tag }}
            </span>
          </div>
        </PageSection>

        <PageSection title="日记内容">
          <div class="prose prose-slate max-w-none">
            <div
              class="diary-content whitespace-pre-wrap text-slate-700 leading-relaxed"
              v-html="diary.content"
            ></div>
          </div>
        </PageSection>
      </div>

      <div
        class="md:w-[360px] md:min-w-[320px] md:overflow-y-auto md:border-l md:border-slate-200 md:pl-6"
      >
        <div class="space-y-6">
          <PageSection title="评价日记">
            <div class="rounded-lg bg-slate-50 p-6">
              <div class="space-y-4">
                <div>
                  <label class="mb-2 block text-sm font-medium text-slate-700">
                    给这篇日记打分
                  </label>
                  <div class="flex items-center gap-1">
                    <button
                      v-for="star in 5"
                      :key="star"
                      :class="[
                        'text-2xl transition-colors',
                        star <= userRating ? 'text-yellow-400' : 'text-slate-300'
                      ]"
                      @click="userRating = star"
                    >
                      ★
                    </button>
                    <span class="ml-2 text-sm text-slate-600">
                      {{ userRating > 0 ? `${userRating} 星` : '点击星星评分' }}
                    </span>
                  </div>
                </div>

                <div>
                  <label class="mb-2 block text-sm font-medium text-slate-700">
                    写下你的评价（可选）
                  </label>
                  <textarea
                    v-model="ratingComment"
                    placeholder="分享你的感受..."
                    class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    rows="3"
                  ></textarea>
                </div>

                <button
                  :disabled="userRating === 0 || isSubmittingRating"
                  class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
                  @click="submitRating"
                >
                  {{ isSubmittingRating ? '提交中...' : '提交评价' }}
                </button>
              </div>
            </div>
          </PageSection>

          <PageSection title="旅友评价">
            <div class="space-y-6">
              <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                <div class="flex flex-col gap-6">
                  <div>
                    <div class="text-4xl font-bold text-slate-800">
                      {{ averageScore.toFixed(1) }}
                    </div>
                    <div class="mt-1 text-sm text-slate-500">
                      基于 {{ ratingsTotal }} 条评分 · {{ commentsCount }} 条评论
                    </div>
                    <div class="mt-2 text-xl text-yellow-400 leading-none">
                      {{ averageScore > 0 ? formatRating(averageScore) : '暂无评分' }}
                    </div>
                  </div>
                  <div class="space-y-2">
                    <div
                      v-for="item in ratingDistribution"
                      :key="item.score"
                    >
                      <div class="flex items-center justify-between text-sm text-slate-500">
                        <span>{{ item.score }} 星</span>
                        <span>{{ item.count }}</span>
                      </div>
                      <div class="h-2 w-full rounded-full bg-slate-200">
                        <div
                          class="h-full rounded-full bg-primary transition-all"
                          :style="{ width: `${item.percentage}%` }"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <LoadingIndicator v-if="isLoadingRatings" message="加载评价..." />

              <div v-else class="space-y-4">
                <template v-if="hasRatings">
                  <div
                    v-for="rating in ratingItems"
                    :key="rating.id"
                    class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div class="text-sm font-semibold text-slate-700">
                          {{ rating.user.username }}
                        </div>
                        <div class="text-xs text-slate-500">@{{ rating.user.username }}</div>
                      </div>
                      <div class="text-xs text-slate-500">
                        {{ formatDateTime(rating.created_at) }}
                      </div>
                    </div>
                    <div class="mt-2 text-lg text-yellow-400 leading-none">
                      {{ renderStars(rating.score) }}
                    </div>
                    <p v-if="rating.comment" class="mt-3 whitespace-pre-line text-sm text-slate-700">
                      {{ rating.comment }}
                    </p>
                  </div>
                </template>
                <EmptyState
                  v-else
                  icon="💬"
                  title="暂无评价"
                  message="快来留下你的第一条评论吧。"
                />

                <div
                  v-if="totalRatingPages > 1"
                  class="mt-4 flex items-center justify-between gap-2 text-sm"
                >
                  <button
                    class="rounded-md border border-slate-200 px-3 py-1 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                    :disabled="ratingsPage === 1"
                    @click="goToRatingsPage(ratingsPage - 1)"
                  >
                    上一页
                  </button>
                  <span class="text-slate-500">
                    第 {{ ratingsPage }} / {{ totalRatingPages }} 页
                  </span>
                  <button
                    class="rounded-md border border-slate-200 px-3 py-1 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                    :disabled="ratingsPage === totalRatingPages"
                    @click="goToRatingsPage(ratingsPage + 1)"
                  >
                    下一页
                  </button>
                </div>
              </div>
            </div>
          </PageSection>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diary-content {
  line-height: 1.7;
}

.diary-content h1,
.diary-content h2,
.diary-content h3 {
  color: #1e293b;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

.diary-content p {
  margin-bottom: 1em;
}

.diary-content img {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.diary-content .diary-media {
  margin: 1.5rem 0;
  text-align: center;
}

.diary-content .diary-media img,
.diary-content .diary-media video {
  max-width: 100%;
  border-radius: 0.75rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.12);
}

.diary-content .diary-media figcaption {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

</style>