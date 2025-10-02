<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const navLinks = [
  { to: '/', label: '旅游推荐' },
  { to: '/routing', label: '路线规划' },
  { to: '/facilities', label: '场所查询' },
  { to: '/diaries', label: '旅游日记' },
]

const route = useRoute()

const activePath = computed(() => route.path)
</script>

<template>
  <div class="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 to-blue-50 text-slate-900">
    <header class="sticky top-0 z-50 border-b border-slate-200/60 bg-white/80 shadow-sm backdrop-blur-lg">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <RouterLink to="/" class="flex items-center gap-3 text-xl font-bold text-primary transition hover:text-primary/80">
          <span class="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-blue-600 text-lg font-black text-white shadow-lg">
            旅
          </span>
          <span class="hidden sm:inline">个性化旅游系统</span>
        </RouterLink>
        <nav class="flex items-center gap-2 text-sm font-medium">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="rounded-lg px-4 py-2 transition-all duration-200"
            :class="
              activePath === link.to
                ? 'bg-primary text-white shadow-lg shadow-primary/30'
                : 'text-slate-600 hover:bg-slate-100 hover:text-primary'
            "
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-4 py-8">
      <RouterView />
    </main>

    <footer class="border-t border-slate-200/60 bg-white/80 py-6 text-sm text-slate-500 backdrop-blur">
      <div class="mx-auto flex max-w-7xl flex-col gap-3 px-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <span class="font-semibold text-slate-700">© {{ new Date().getFullYear() }} 个性化旅游系统</span>
          <span class="hidden sm:inline">·</span>
          <span class="text-xs">数据结构课程设计</span>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <span class="rounded bg-blue-100 px-2 py-1 font-medium text-blue-700">FastAPI</span>
          <span class="rounded bg-green-100 px-2 py-1 font-medium text-green-700">Vue 3</span>
          <span class="rounded bg-cyan-100 px-2 py-1 font-medium text-cyan-700">Tailwind CSS</span>
        </div>
      </div>
    </footer>
  </div>
</template>
