<script setup lang="ts">
interface Props {
  title?: string
  description?: string
  icon?: string
}

defineProps<Props>()
</script>

<template>
  <div class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-200 bg-white/70 p-6 text-center text-slate-500">
    <span v-if="icon" class="text-2xl" aria-hidden="true">{{ icon }}</span>
    <h3 v-if="title" class="text-base font-medium text-slate-800">{{ title }}</h3>
    <p v-if="description" class="text-sm text-slate-500">{{ description }}</p>
    <slot />
  </div>
</template>
