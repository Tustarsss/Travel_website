/**
 * Pinia store for diary state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  DiaryListItem,
  DiaryDetail,
  DiarySortBy,
  DiaryStatus,
} from '../types/diary'

export const useDiariesStore = defineStore('diaries', () => {
  // State
  const currentDiary = ref<DiaryDetail | null>(null)
  const diaryList = ref<DiaryListItem[]>([])
  
  // Filters (persisted)
  const filters = ref({
    sortBy: 'hybrid' as DiarySortBy,
    interests: [] as string[],
    regionId: null as number | null,
    search: '',
    fullTextSearch: '',
    status: null as DiaryStatus | null,
  })
  
  // Pagination
  const pagination = ref({
    page: 1,
    pageSize: 10,
    total: 0,
  })

  // Computed
  const hasFilters = computed(() => {
    return (
      filters.value.regionId !== null ||
      filters.value.interests.length > 0 ||
      filters.value.search !== '' ||
      filters.value.status !== null
    )
  })

  // Actions
  function setCurrentDiary(diary: DiaryDetail | null) {
    currentDiary.value = diary
  }

  function setDiaryList(diaries: DiaryListItem[]) {
    diaryList.value = diaries
  }

  function setSortBy(sortBy: DiarySortBy) {
    filters.value.sortBy = sortBy
  }

  function setInterests(interests: string[]) {
    filters.value.interests = interests
  }

  function setRegionId(regionId: number | null) {
    filters.value.regionId = regionId
  }

  function setSearch(search: string) {
    filters.value.search = search
  }

  function setFullTextSearch(fullTextSearch: string) {
    filters.value.fullTextSearch = fullTextSearch
  }

  function setStatus(status: DiaryStatus | null) {
    filters.value.status = status
  }

  function resetFilters() {
    filters.value = {
      sortBy: 'hybrid',
      interests: [],
      regionId: null,
      search: '',
      fullTextSearch: '',
      status: null,
    }
  }

  function setPagination(page: number, pageSize: number, total: number) {
    pagination.value = { page, pageSize, total }
  }

  function updateDiaryInList(updatedDiary: DiaryListItem) {
    const index = diaryList.value.findIndex((d) => d.id === updatedDiary.id)
    if (index !== -1) {
      diaryList.value[index] = updatedDiary
    }
  }

  function removeDiaryFromList(diaryId: number) {
    diaryList.value = diaryList.value.filter((d) => d.id !== diaryId)
  }

  return {
    // State
    currentDiary,
    diaryList,
    filters,
    pagination,
    
    // Computed
    hasFilters,
    
    // Actions
    setCurrentDiary,
    setDiaryList,
    setSortBy,
    setInterests,
    setRegionId,
    setSearch,
    setFullTextSearch,
    setStatus,
    resetFilters,
    setPagination,
    updateDiaryInList,
    removeDiaryFromList,
  }
})
