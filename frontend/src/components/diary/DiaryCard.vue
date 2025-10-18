<template>
  <div
    class="diary-card group cursor-pointer overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition-all hover:shadow-md"
    @click="handleClick"
  >
    <!-- Cover Image -->
    <div
      v-if="diary.cover_image"
      class="relative aspect-video w-full overflow-hidden bg-slate-100"
    >
      <img
        :src="diary.cover_image"
        :alt="diary.title"
        class="h-full w-full object-cover transition-transform group-hover:scale-105"
        loading="lazy"
      />
      <!-- Status Badges -->
      <div class="absolute right-2 top-2 flex flex-col gap-1">
        <!-- Draft Status -->
        <div
          v-if="diary.status === 'draft'"
          class="rounded-full bg-yellow-500 px-3 py-1 text-xs font-medium text-white"
        >
          草稿
        </div>
        <!-- Compression Status -->
        <div
          v-if="showCompressionStatus && (diary as any).is_compressed"
          class="rounded-full bg-green-500 px-3 py-1 text-xs font-medium text-white"
        >
          已压缩
        </div>
      </div>

      <!-- Animation Preview -->
      <div
        v-if="animationThumbnail"
        class="absolute bottom-2 right-2 rounded bg-black/50 p-1"
      >
        <div class="flex items-center gap-1 text-xs text-white">
          <span>🎬</span>
          <span>动画</span>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="p-4">
      <!-- Title -->
      <h3 class="mb-2 line-clamp-2 text-lg font-semibold text-slate-800 group-hover:text-primary">
        {{ diary.title }}
      </h3>

      <!-- Content Preview -->
      <p v-if="contentPreview" class="mb-3 line-clamp-2 text-sm text-slate-600">
        {{ contentPreview }}
      </p>

      <!-- Meta Info -->
      <div class="mb-3 flex items-center gap-4 text-xs text-slate-500">
        <div class="flex items-center gap-1">
          <span>👁️</span>
          <span>{{ formatNumber(diary.popularity) }}</span>
        </div>
        <div class="flex items-center gap-1">
          <span>⭐</span>
          <span>{{ diary.rating.toFixed(1) }}</span>
          <span class="text-slate-400">({{ diary.ratings_count }})</span>
        </div>
        <div v-if="diary.comments_count > 0" class="flex items-center gap-1">
          <span>💬</span>
          <span>{{ diary.comments_count }}</span>
        </div>
        <!-- Recommendation Score -->
        <div v-if="recommendationScore !== undefined" class="flex items-center gap-1">
          <span>🎯</span>
          <span>{{ recommendationScore.toFixed(2) }}</span>
        </div>
      </div>

      <!-- Author and Region -->
      <div class="mb-3 flex items-center justify-between text-xs text-slate-500">
        <div class="flex items-center gap-2">
          <div
            class="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary"
          >
            {{ diary.author.username.charAt(0) }}
          </div>
          <span>{{ diary.author.username }}</span>
        </div>
        <div class="flex items-center gap-1">
          <span>📍</span>
          <span>{{ diary.region.name || '未知地点' }}</span>
        </div>
      </div>

      <!-- Tags -->
      <div v-if="diary.tags && diary.tags.length > 0" class="flex flex-wrap gap-1">
        <span
          v-for="tag in diary.tags.slice(0, 3)"
          :key="tag"
          class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
        >
          {{ tag }}
        </span>
        <span
          v-if="diary.tags.length > 3"
          class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-400"
        >
          +{{ diary.tags.length - 3 }}
        </span>
      </div>

      <!-- Date -->
      <div class="mt-3 text-xs text-slate-400">
        {{ formatDate(diary.created_at) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiaryListItem } from '../../types/diary'

interface Props {
  diary: DiaryListItem
  showCompressionStatus?: boolean
  recommendationScore?: number
  animationThumbnail?: string
}

interface Emits {
  (e: 'click', diary: DiaryListItem): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const contentPreview = computed(() => props.diary.content_preview?.trim() ?? '')

const handleClick = () => {
  emit('click', props.diary)
}

const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return '今天'
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else if (days < 30) {
    return `${Math.floor(days / 7)}周前`
  } else if (days < 365) {
    return `${Math.floor(days / 30)}个月前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-clamp: 2;
  overflow: hidden;
}
</style>
