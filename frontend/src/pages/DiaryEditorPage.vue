<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageSection from '../components/ui/PageSection.vue'
import KeywordSearchSelect, { type SearchOption } from '../components/ui/KeywordSearchSelect.vue'
import TagInput from '../components/ui/TagInput.vue'
import SuccessAlert from '../components/ui/SuccessAlert.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import { useApiRequest } from '../composables/useApiRequest'
import { createDiary, searchRegions } from '../services/api'
import type {
  DiaryCreateRequest,
  DiaryCreateResponse,
  DiaryMediaType,
  DiaryStatus,
} from '../types/diary'
import type { RegionSearchResult } from '../types/api'

interface MediaItem {
  url: string
  type: DiaryMediaType
}

const router = useRouter()

const form = reactive({
  title: '',
  summary: '',
  content: '',
  status: 'published' as DiaryStatus,
})

const selectedRegion = ref<SearchOption<RegionSearchResult> | null>(null)
const tags = ref<string[]>([])
const mediaItems = ref<MediaItem[]>([
  { url: '', type: 'image' },
])

const createdDiary = ref<DiaryCreateResponse | null>(null)
const submitted = ref(false)
const touched = reactive({
  title: false,
  region: false,
  content: false,
})

const mediaTypeOptions: Array<{ value: DiaryMediaType; label: string }> = [
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
]

const statusOptions: Array<{ value: DiaryStatus; label: string; description: string }> = [
  { value: 'published', label: '立即发布', description: '创建后立即公开展示' },
  { value: 'draft', label: '保存草稿', description: '暂不公开，可稍后继续编辑' },
]

const {
  execute: submitDiary,
  loading: submitting,
  error: submitError,
} = useApiRequest(createDiary)

const handleRegionSearch = async (keyword: string) => {
  const results = await searchRegions({ keyword, limit: 8 })
  return results.map((region) => ({
    id: region.id,
    label: region.name,
    description: [region.city, region.type === 'scenic' ? '景区' : region.type === 'campus' ? '校园' : null]
      .filter(Boolean)
      .join(' · '),
    payload: region,
  })) as SearchOption<RegionSearchResult>[]
}

const filteredMedia = computed(() => {
  return mediaItems.value
    .map((item) => ({
      url: item.url.trim(),
      type: item.type,
    }))
    .filter((item) => item.url.length > 0)
})

const invalidMediaItems = computed(() => {
  return filteredMedia.value.filter((item) => !/^https?:\/\//i.test(item.url))
})

const titleError = computed(() => {
  if (!touched.title && !submitted.value) return null
  if (!form.title.trim()) return '请输入日记标题'
  if (form.title.trim().length > 200) return '标题不能超过 200 个字符'
  return null
})

const regionError = computed(() => {
  if (!touched.region && !submitted.value) return null
  if (!selectedRegion.value) return '请选择关联的地区'
  return null
})

const contentError = computed(() => {
  if (!touched.content && !submitted.value) return null
  const length = form.content.trim().length
  if (length === 0) return '请输入日记正文内容'
  if (length < 10) return '正文内容至少需要 10 个字符'
  return null
})

const mediaError = computed(() => {
  if (invalidMediaItems.value.length === 0) return null
  return '媒体链接需以 http 或 https 开头'
})

const canSubmit = computed(() => {
  const titleLength = form.title.trim().length
  const contentLengthValue = form.content.trim().length
  return (
    titleLength > 0 &&
    titleLength <= 200 &&
    !!selectedRegion.value &&
    contentLengthValue >= 10 &&
    invalidMediaItems.value.length === 0
  )
})

const summaryLength = computed(() => form.summary.trim().length)
const contentLength = computed(() => form.content.trim().length)

const addMediaItem = () => {
  mediaItems.value = [...mediaItems.value, { url: '', type: 'image' }]
}

const removeMediaItem = (index: number) => {
  if (mediaItems.value.length === 1) {
    mediaItems.value = [{ url: '', type: 'image' }]
    return
  }
  mediaItems.value = mediaItems.value.filter((_, i) => i !== index)
}

const resetForm = () => {
  form.title = ''
  form.summary = ''
  form.content = ''
  form.status = 'published'
  selectedRegion.value = null
  tags.value = []
  mediaItems.value = [{ url: '', type: 'image' }]
  createdDiary.value = null
  submitted.value = false
  touched.title = false
  touched.region = false
  touched.content = false
}

const handleSubmit = async () => {
  submitted.value = true
  touched.title = true
  touched.region = true
  touched.content = true

  if (!canSubmit.value || submitting.value || !selectedRegion.value) {
    return
  }

  const media = filteredMedia.value
  const payload: DiaryCreateRequest = {
    title: form.title.trim(),
    summary: form.summary.trim() || undefined,
    content: form.content.trim(),
    region_id: Number(selectedRegion.value.id),
    tags: tags.value,
    media_urls: media.map((item) => item.url),
    media_types: media.map((item) => item.type),
    status: form.status,
  }

  try {
    const response = await submitDiary(payload)
    createdDiary.value = response
  } catch (error) {
    console.error('Failed to create diary', error)
    createdDiary.value = null
  }
}

const goToDiaryDetail = () => {
  if (!createdDiary.value) return
  void router.push({ name: 'diary-detail', params: { id: createdDiary.value.id } })
}

const handleFocus = (field: 'title' | 'region' | 'content') => {
  touched[field] = true
}
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="撰写旅行日记"
      description="记录旅途中的精彩瞬间，分享你的独特体验"
    >
      <div class="mx-auto max-w-3xl space-y-6">
        <SuccessAlert
          v-if="createdDiary"
          :message="`日记《${createdDiary.title}》创建成功！`"
        />

        <ErrorAlert
          v-else-if="submitError"
          :message="submitError.message || '创建日记失败，请稍后再试。'"
        />

        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- 基本信息 -->
          <div class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <label class="block text-sm font-medium text-slate-700">日记标题 *</label>
              <input
                v-model="form.title"
                type="text"
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="例如：西湖漫步，一日慢旅行"
                maxlength="200"
                @focus="handleFocus('title')"
              />
              <p v-if="titleError" class="mt-2 text-xs text-red-500">{{ titleError }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700">关联地区 *</label>
              <KeywordSearchSelect
                v-model="selectedRegion"
                class="mt-2"
                :search="handleRegionSearch"
                placeholder="搜索景区或园区"
                @select="() => (touched.region = true)"
                @clear="() => (touched.region = true)"
              />
              <p v-if="regionError" class="mt-2 text-xs text-red-500">{{ regionError }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700">摘要</label>
              <textarea
                v-model="form.summary"
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                rows="3"
                placeholder="用几句话概括这次旅行的亮点"
                maxlength="500"
              ></textarea>
              <div class="mt-1 text-right text-xs text-slate-400">
                {{ summaryLength }} / 500
              </div>
            </div>
          </div>

          <!-- 标签与媒体 -->
          <div class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <label class="block text-sm font-medium text-slate-700">标签</label>
              <TagInput v-model="tags" :max-tags="10" class="mt-2" />
              <p class="mt-1 text-xs text-slate-400">示例：美食、自然、亲子、夜景</p>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <label class="block text-sm font-medium text-slate-700">媒体资源</label>
                <button
                  type="button"
                  class="rounded-full border border-dashed border-primary/70 px-3 py-1 text-xs text-primary transition-colors hover:bg-primary/5"
                  @click="addMediaItem"
                >
                  + 添加链接
                </button>
              </div>

              <div class="space-y-3">
                <div
                  v-for="(item, index) in mediaItems"
                  :key="index"
                  class="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4 md:flex-row md:items-center"
                >
                  <div class="flex-1">
                    <input
                      v-model="item.url"
                      type="url"
                      class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                      placeholder="https://example.com/photo.jpg"
                    />
                  </div>
                  <div class="flex items-center gap-3">
                    <select
                      v-model="item.type"
                      class="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      <option
                        v-for="option in mediaTypeOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.label }}
                      </option>
                    </select>
                    <button
                      type="button"
                      class="text-xs text-slate-400 transition-colors hover:text-red-500"
                      @click="removeMediaItem(index)"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
              <p v-if="mediaError" class="text-xs text-red-500">{{ mediaError }}</p>
            </div>
          </div>

          <!-- 内容与发布状态 -->
          <div class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <label class="block text-sm font-medium text-slate-700">日记正文 *</label>
              <textarea
                v-model="form.content"
                class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm leading-relaxed focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                rows="10"
                placeholder="详细描述你的旅程、感受与推荐……"
                @focus="handleFocus('content')"
              ></textarea>
              <div class="mt-1 flex items-center justify-between text-xs text-slate-400">
                <span>{{ contentLength }} 字</span>
                <span>内容不少于 10 字</span>
              </div>
              <p v-if="contentError" class="mt-2 text-xs text-red-500">{{ contentError }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700">发布设置</label>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <label
                  v-for="option in statusOptions"
                  :key="option.value"
                  class="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-primary/70"
                >
                  <input
                    v-model="form.status"
                    type="radio"
                    name="diary-status"
                    :value="option.value"
                    class="mt-1 h-4 w-4 border-primary text-primary focus:ring-primary"
                  />
                  <div>
                    <div class="text-sm font-medium text-slate-700">{{ option.label }}</div>
                    <div class="mt-1 text-xs text-slate-500">{{ option.description }}</div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div class="text-xs text-slate-400">带 * 为必填项</div>
            <div class="flex items-center gap-3">
              <button
                type="submit"
                class="rounded-full bg-primary px-6 py-2 text-sm font-medium text-white shadow-md transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="submitting || !canSubmit"
              >
                {{ submitting ? '保存中…' : form.status === 'draft' ? '保存草稿' : '发布日记' }}
              </button>
              <button
                v-if="createdDiary"
                type="button"
                class="rounded-full border border-primary px-6 py-2 text-sm font-medium text-primary transition hover:bg-primary/10"
                @click="goToDiaryDetail"
              >
                查看详情
              </button>
              <button
                v-if="createdDiary"
                type="button"
                class="rounded-full border border-slate-300 px-6 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
                @click="resetForm"
              >
                继续撰写
              </button>
            </div>
          </div>
        </form>
      </div>
    </PageSection>
  </div>
</template>
