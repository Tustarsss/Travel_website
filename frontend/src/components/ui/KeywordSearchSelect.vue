<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface SearchOption<TPayload = unknown> {
  id: string | number
  label: string
  description?: string
  payload?: TPayload
}

const props = withDefaults(
  defineProps<{
    modelValue: SearchOption | null
    search: (keyword: string) => Promise<SearchOption[]>
    placeholder?: string
    disabled?: boolean
    debounce?: number
    minLength?: number
    emptyText?: string
    loadingText?: string
    noResultsText?: string
    errorText?: string
  }>(),
  {
    modelValue: null,
    placeholder: '请输入关键词',
    disabled: false,
    debounce: 220,
    minLength: 2,
    emptyText: '输入至少两个字符开始搜索',
    loadingText: '搜索中…',
    noResultsText: '未找到匹配项',
    errorText: '搜索失败，请稍后重试',
  }
)

const emit = defineEmits<{
  'update:modelValue': [SearchOption | null]
  select: [SearchOption]
  clear: []
}>()

const rootRef = ref<HTMLDivElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const searchTerm = ref(props.modelValue?.label ?? '')
const isOpen = ref(false)
const suggestions = ref<SearchOption[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
let requestToken = 0
let timeoutHandle: number | null = null

const hasValue = computed(() => searchTerm.value.trim().length > 0)

const clearPending = () => {
  if (timeoutHandle !== null) {
    clearTimeout(timeoutHandle)
    timeoutHandle = null
  }
}

const closeDropdown = () => {
  isOpen.value = false
}

const openDropdown = () => {
  if (props.disabled) return
  isOpen.value = true
}

const scheduleSearch = (keyword: string) => {
  clearPending()
  const trimmed = keyword.trim()
  if (trimmed.length < props.minLength) {
    suggestions.value = []
    loading.value = false
    errorMessage.value = null
    return
  }

  timeoutHandle = window.setTimeout(() => {
    void runSearch(trimmed)
  }, props.debounce)
}

const runSearch = async (keyword: string) => {
  requestToken += 1
  const currentToken = requestToken
  loading.value = true
  errorMessage.value = null

  try {
    const results = await props.search(keyword)
    if (currentToken === requestToken) {
      suggestions.value = results
      isOpen.value = true
    }
  } catch (error) {
    if (currentToken === requestToken) {
      const message = error instanceof Error ? error.message : props.errorText
      errorMessage.value = message ?? props.errorText
      suggestions.value = []
    }
  } finally {
    if (currentToken === requestToken) {
      loading.value = false
    }
  }
}

const handleInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  searchTerm.value = value
  openDropdown()
  scheduleSearch(value)
}

const handleFocus = () => {
  openDropdown()
  if (hasValue.value) {
    scheduleSearch(searchTerm.value)
  }
}

const handleSelection = (option: SearchOption) => {
  emit('update:modelValue', option)
  emit('select', option)
  searchTerm.value = option.label
  closeDropdown()
  suggestions.value = []
}

const handleClear = () => {
  emit('update:modelValue', null)
  emit('clear')
  searchTerm.value = ''
  suggestions.value = []
  errorMessage.value = null
  loading.value = false
  requestToken += 1
}

const handleDocumentClick = (event: MouseEvent) => {
  if (!rootRef.value) return
  if (rootRef.value.contains(event.target as Node)) {
    return
  }
  closeDropdown()
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    closeDropdown()
    inputRef.value?.blur()
  }
}

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      searchTerm.value = ''
      return
    }
    searchTerm.value = value.label
  }
)

watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      closeDropdown()
    }
  }
)

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentClick)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
  document.removeEventListener('keydown', handleKeydown)
  clearPending()
})
</script>

<template>
  <div ref="rootRef" class="search-select" :class="{ 'is-disabled': disabled }">
    <div class="input-wrapper">
      <input
        ref="inputRef"
        :value="searchTerm"
        class="search-input"
        type="text"
        :placeholder="placeholder"
        :disabled="disabled"
        @focus="handleFocus"
        @input="handleInput"
      />
      <button
        v-if="hasValue && !disabled"
        type="button"
        class="clear-button"
        title="清除"
        @mousedown.prevent="handleClear"
      >
        ×
      </button>
    </div>
    <transition name="dropdown-fade">
      <div v-if="isOpen && !disabled" class="dropdown">
        <div v-if="searchTerm.trim().length < minLength" class="dropdown-message">
          {{ emptyText }}
        </div>
        <div v-else-if="loading" class="dropdown-message dropdown-loading">
          {{ loadingText }}
        </div>
        <div v-else-if="errorMessage" class="dropdown-message dropdown-error">
          {{ errorMessage }}
        </div>
        <ul v-else-if="suggestions.length" class="suggestion-list">
          <li v-for="option in suggestions" :key="option.id">
            <button type="button" class="suggestion-item" @mousedown.prevent="handleSelection(option)">
              <span class="suggestion-label">{{ option.label }}</span>
              <span v-if="option.description" class="suggestion-desc">{{ option.description }}</span>
            </button>
          </li>
        </ul>
        <div v-else class="dropdown-message dropdown-empty">
          {{ noResultsText }}
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.search-select {
  position: relative;
  width: 100%;
}

.input-wrapper {
  position: relative;
}

.search-input {
  width: 100%;
  border-radius: 0.65rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  padding: 0.65rem 0.9rem;
  font-size: 0.85rem;
  color: #0f172a;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  background-color: white;
}

.search-input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.7);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.clear-button {
  position: absolute;
  right: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: rgba(226, 232, 240, 0.65);
  color: #475569;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 9999px;
  font-size: 1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease;
}

.clear-button:hover {
  background: rgba(148, 163, 184, 0.65);
}

.dropdown {
  position: absolute;
  inset-inline-start: 0;
  top: calc(100% + 4px);
  width: 100%;
  border-radius: 0.85rem;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 40px -35px rgba(15, 23, 42, 0.45);
  z-index: 20;
  overflow: hidden;
}

.dropdown-message {
  padding: 0.75rem 1rem;
  font-size: 0.78rem;
  color: #64748b;
}

.dropdown-loading {
  color: #1d4ed8;
}

.dropdown-error {
  color: #dc2626;
}

.dropdown-empty {
  color: #475569;
}

.suggestion-list {
  max-height: 14rem;
  overflow-y: auto;
  margin: 0;
  padding: 0.35rem;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.suggestion-item {
  width: 100%;
  text-align: left;
  border: none;
  background: rgba(248, 250, 252, 0.65);
  border-radius: 0.75rem;
  padding: 0.55rem 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  color: #0f172a;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.suggestion-item:hover {
  background: rgba(191, 219, 254, 0.55);
  transform: translateY(-1px);
}

.suggestion-label {
  font-weight: 600;
}

.suggestion-desc {
  font-size: 0.72rem;
  color: #64748b;
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.is-disabled .search-input {
  background: rgba(226, 232, 240, 0.3);
  color: #94a3b8;
  cursor: not-allowed;
}

.is-disabled .clear-button {
  display: none;
}
</style>
