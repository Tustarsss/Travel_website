<script setup lang="ts">
interface Props {
  title: string
  description?: string
}

defineProps<Props>()
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
    <header v-if="title || description || $slots.actions" class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="space-y-1">
        <h2 class="text-xl font-semibold text-slate-900">{{ title }}</h2>
        <p v-if="description" class="text-sm text-slate-500">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </header>
    <div class="space-y-4">
      <slot />
    </div>
  </section>
</template>
