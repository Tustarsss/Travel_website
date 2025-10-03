<template>
  <div class="animation-generator">
    <!-- Generate Button -->
    <button
      v-if="!animationData"
      :disabled="isGenerating"
      class="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
      @click="generateAnimation"
    >
      <span v-if="isGenerating" class="animate-spin">⏳</span>
      <span v-else>🎬</span>
      <span>{{ isGenerating ? '生成中...' : '生成动画' }}</span>
    </button>

    <!-- Animation Display -->
    <div v-else class="animation-display space-y-3">
      <!-- Video Player -->
      <div v-if="animationData.video_url" class="video-player">
        <video
          :src="animationData.video_url"
          controls
          class="w-full rounded-lg"
          :poster="animationData.thumbnail_url"
        >
          您的浏览器不支持视频播放。
        </video>
      </div>

      <!-- Progress Bar (if still processing) -->
      <div v-if="animationData.status === 'processing'" class="progress-section">
        <div class="flex items-center justify-between text-sm text-slate-600 mb-2">
          <span>生成进度</span>
          <span>{{ animationData.progress }}%</span>
        </div>
        <div class="w-full bg-slate-200 rounded-full h-2">
          <div
            class="bg-primary h-2 rounded-full transition-all duration-300"
            :style="{ width: `${animationData.progress}%` }"
          ></div>
        </div>
        <p class="text-xs text-slate-500 mt-1">正在生成动画，请稍候...</p>
      </div>

      <!-- Status Messages -->
      <div class="status-message">
        <div v-if="animationData.status === 'completed'" class="text-green-600 text-sm">
          ✅ 动画生成完成
        </div>
        <div v-else-if="animationData.status === 'failed'" class="text-red-600 text-sm">
          ❌ 生成失败: {{ animationData.error_message || '未知错误' }}
        </div>
        <div v-else-if="animationData.status === 'pending'" class="text-yellow-600 text-sm">
          ⏳ 等待处理
        </div>
      </div>

      <!-- Regenerate Button -->
      <button
        v-if="animationData.status === 'completed' || animationData.status === 'failed'"
        class="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1 text-sm text-slate-600 hover:bg-slate-50"
        @click="regenerateAnimation"
      >
        <span>🔄</span>
        <span>重新生成</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { generateDiaryAnimation } from '../../services/api'
import type { DiaryAnimation, AnimationGenerateRequest } from '../../types/diary'

interface Props {
  diaryId: number
  style?: string
  duration?: number
  customDescription?: string
}

interface Emits {
  (e: 'animationGenerated', animation: DiaryAnimation): void
  (e: 'animationUpdated', animation: DiaryAnimation): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// State
const animationData = ref<DiaryAnimation | null>(null)
const isGenerating = ref(false)
const pollInterval = ref<number | null>(null)

// Methods
const generateAnimation = async () => {
  if (isGenerating.value) return

  try {
    isGenerating.value = true

    const request: AnimationGenerateRequest = {
      style: props.style,
      duration: props.duration,
      custom_description: props.customDescription,
    }

    // Generate animation
    const animation = await generateDiaryAnimation(props.diaryId, request)
    animationData.value = animation
    emit('animationGenerated', animation)

    // If still processing, start polling
    if (animation.status === 'processing' || animation.status === 'pending') {
      startPolling()
    }

  } catch (error) {
    console.error('Failed to generate animation:', error)
    // Could emit error event here
  } finally {
    isGenerating.value = false
  }
}

const regenerateAnimation = async () => {
  animationData.value = null
  await generateAnimation()
}

const startPolling = () => {
  // Poll every 3 seconds by regenerating (since we don't have a separate status endpoint)
  pollInterval.value = window.setInterval(async () => {
    try {
      // For now, we'll just regenerate to check status
      // In a real implementation, you'd have a separate status endpoint
      const animation = await generateDiaryAnimation(props.diaryId, {})
      animationData.value = animation
      emit('animationUpdated', animation)

      // Stop polling if completed or failed
      if (animation.status === 'completed' || animation.status === 'failed') {
        stopPolling()
      }
    } catch (error) {
      console.error('Failed to poll animation status:', error)
      stopPolling()
    }
  }, 3000)
}

const stopPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

// Watch for diary ID changes
watch(() => props.diaryId, () => {
  stopPolling()
  animationData.value = null
  // Note: We don't load existing animations since we don't have a status endpoint
}, { immediate: true })

// Cleanup on unmount
const cleanup = () => {
  stopPolling()
}

// Expose cleanup method
defineExpose({ cleanup })
</script>