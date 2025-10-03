<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    placeholder?: string
    maxTags?: number
    disabled?: boolean
  }>(),
  {
    modelValue: () => [],
    placeholder: '输入标签并按回车',
    maxTags: 10,
    disabled: false,
  }
)

const emit = defineEmits<{
  'update:modelValue': [string[]]
  change: [string[]]
}>()

const inputValue = ref('')
const pendingTags = ref<string[]>([...props.modelValue])

watch(
  () => props.modelValue,
  (value) => {
    pendingTags.value = [...(value ?? [])]
  }
)

const hasReachedLimit = computed(() => pendingTags.value.length >= props.maxTags)
const remainingCount = computed(() => Math.max(props.maxTags - pendingTags.value.length, 0))
const inputPlaceholder = computed(() => {
  if (hasReachedLimit.value) {
    return '已达到标签数量上限'
  }
  if (remainingCount.value < props.maxTags) {
    return `还可添加 ${remainingCount.value} 个标签`
  }
  return props.placeholder
})

const normalizeTag = (tag: string): string | null => {
  const trimmed = tag.trim()
  if (!trimmed) return null
  if (trimmed.length > 30) {
    return trimmed.slice(0, 30)
  }
  return trimmed
}

const emitUpdate = (tags: string[]) => {
  emit('update:modelValue', tags)
  emit('change', tags)
}

const addTag = () => {
  if (props.disabled || hasReachedLimit.value) return
  const normalized = normalizeTag(inputValue.value)
  if (!normalized) {
    inputValue.value = ''
    return
  }
  if (pendingTags.value.some((tag) => tag.toLowerCase() === normalized.toLowerCase())) {
    inputValue.value = ''
    return
  }
  pendingTags.value = [...pendingTags.value, normalized]
  emitUpdate(pendingTags.value)
  inputValue.value = ''
}

const removeTag = (tag: string) => {
  if (props.disabled) return
  pendingTags.value = pendingTags.value.filter((item) => item !== tag)
  emitUpdate(pendingTags.value)
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addTag()
  } else if (event.key === 'Backspace' && inputValue.value === '') {
    const last = pendingTags.value[pendingTags.value.length - 1]
    if (last) {
      removeTag(last)
    }
  }
}

const handleBlur = () => {
  if (inputValue.value.trim()) {
    addTag()
  }
}
</script>

<template>
  <div class="space-y-2">
    <div
      class="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-3 transition-colors"
      :class="[
        disabled ? 'bg-slate-50 opacity-70' : 'focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10',
        hasReachedLimit ? 'border-dashed border-primary/60' : ''
      ]"
    >
      <span
        v-for="tag in pendingTags"
        :key="tag"
        class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
      >
        #{{ tag }}
        <button
          v-if="!disabled"
          type="button"
          class="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary/20 text-primary/80 transition-colors hover:bg-primary hover:text-white"
          @click="removeTag(tag)"
        >
          ×
        </button>
      </span>

      <input
        v-if="!hasReachedLimit && !disabled"
        v-model="inputValue"
        class="min-w-[8rem] flex-1 border-none bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
        :placeholder="inputPlaceholder"
        @keydown="handleKeydown"
        @blur="handleBlur"
      />
    </div>
    <p class="text-xs text-slate-400">最多可添加 {{ props.maxTags }} 个标签。</p>
  </div>
</template>
