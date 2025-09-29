<script setup lang="ts">
interface Props {
  label?: string
}

defineProps<Props>()
</script>

<template>
  <div class="flex items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-white/70 p-6 text-slate-500">
    <svg class="h-5 w-5 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
    <span class="text-sm">{{ label ?? '正在加载，请稍候…' }}</span>
  </div>
</template>
