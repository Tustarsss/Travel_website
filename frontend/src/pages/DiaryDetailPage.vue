<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageSection from '../components/ui/PageSection.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import AnimationGenerator from '../components/diary/AnimationGenerator.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { fetchDiaryDetail, rateDiary } from '../services/api'
import type { DiaryRatingRequest } from '../types/diary'

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

// Load diary on mount
onMounted(async () => {
  if (diaryId.value) {
    await loadDiary(diaryId.value)
    // Initialize user rating if available
    if (diary.value) {
      // In a real app, you'd fetch the user's existing rating
      userRating.value = 0
    }
  }
})

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

    // Clear form
    ratingComment.value = ''

  } catch (error) {
    console.error('Failed to submit rating:', error)
  } finally {
    isSubmittingRating.value = false
  }
}

// Handle animation generation
const handleAnimationGenerated = (animation: any) => {
  console.log('Animation generated:', animation)
  // Could update diary data or show notification
}

const handleAnimationUpdated = (animation: any) => {
  console.log('Animation updated:', animation)
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

// Format rating stars
const formatRating = (rating: number): string => {
  return '⭐'.repeat(Math.floor(rating)) + (rating % 1 >= 0.5 ? '⭐' : '')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingIndicator v-if="loading" message="加载日记详情..." />

    <!-- Error State -->
    <ErrorAlert v-else-if="error" :message="error.message" />

    <!-- Diary Content -->
    <div v-else-if="diary" class="space-y-6">
      <!-- Header Section -->
      <PageSection :title="diary.title" :description="`由 ${diary.author.display_name} 发布`">
        <!-- Meta Information -->
        <div class="flex flex-wrap items-center gap-4 text-sm text-slate-600 mb-4">
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

        <!-- Tags -->
        <div v-if="diary.tags && diary.tags.length > 0" class="flex flex-wrap gap-2 mb-4">
          <span
            v-for="tag in diary.tags"
            :key="tag"
            class="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary"
          >
            #{{ tag }}
          </span>
        </div>

        <!-- Summary -->
        <div v-if="diary.summary" class="bg-slate-50 p-4 rounded-lg mb-6">
          <h3 class="font-medium text-slate-800 mb-2">摘要</h3>
          <p class="text-slate-600">{{ diary.summary }}</p>
        </div>
      </PageSection>

      <!-- Content Section -->
      <PageSection title="日记内容">
        <div class="prose prose-slate max-w-none">
          <!-- Content -->
          <div
            class="diary-content whitespace-pre-wrap text-slate-700 leading-relaxed"
            v-html="diary.content"
          ></div>

          <!-- Media Gallery -->
          <div v-if="diary.media_urls && diary.media_urls.length > 0" class="mt-6">
            <h4 class="font-medium text-slate-800 mb-3">图片</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div
                v-for="(url, index) in diary.media_urls"
                :key="index"
                class="aspect-video rounded-lg overflow-hidden bg-slate-100"
              >
                <img
                  :src="url"
                  :alt="`图片 ${index + 1}`"
                  class="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </div>
      </PageSection>

      <!-- Animation Section -->
      <PageSection title="AI动画生成">
        <div class="bg-slate-50 p-6 rounded-lg">
          <p class="text-slate-600 mb-4">
            使用AI技术为这段旅行经历生成精美的动画短片，让美好回忆更加生动。
          </p>
          <AnimationGenerator
            :diary-id="diary.id"
            :duration="30"
            :custom-description="'根据日记内容生成旅行动画'"
            @animation-generated="handleAnimationGenerated"
            @animation-updated="handleAnimationUpdated"
          />
        </div>
      </PageSection>

      <!-- Rating Section -->
      <PageSection title="评价日记">
        <div class="bg-slate-50 p-6 rounded-lg">
          <div class="space-y-4">
            <!-- Rating Stars -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
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

            <!-- Comment -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                写下你的评价（可选）
              </label>
              <textarea
                v-model="ratingComment"
                placeholder="分享你的感受..."
                class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                rows="3"
              ></textarea>
            </div>

            <!-- Submit Button -->
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
    </div>

    <!-- Not Found State -->
    <EmptyState
      v-else
      icon="📝"
      title="日记不存在"
      message="找不到这篇日记，可能已被删除或不存在。"
    />
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
</style>