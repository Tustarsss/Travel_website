<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const navLinks = [
  { to: '/', label: '智能推荐' },
  { to: '/routing', label: '路线规划' },
  { to: '/facilities', label: '设施查询' },
]

const route = useRoute()

const activePath = computed(() => route.path)
</script>

<template>
  <div class="flex min-h-screen flex-col bg-slate-50 text-slate-900">
    <header class="border-b border-slate-200 bg-white/70 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <RouterLink to="/" class="flex items-center gap-2 text-lg font-semibold text-primary">
          <span class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-bold">旅</span>
          个性化旅游系统
        </RouterLink>
        <nav class="flex items-center gap-1 text-sm font-medium text-slate-600">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="rounded-md px-3 py-2 transition"
            :class="
              activePath === link.to
                ? 'bg-primary text-white shadow'
                : 'hover:bg-slate-100 hover:text-primary'
            "
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8">
      <RouterView />
    </main>

    <footer class="border-t border-slate-200 bg-white py-4 text-sm text-slate-500">
      <div class="mx-auto flex max-w-6xl justify-between px-4">
        <span>© {{ new Date().getFullYear() }} 个性化旅游系统</span>
        <span>后端服务：FastAPI · 前端：Vue 3 + Tailwind</span>
      </div>
    </footer>
  </div>
</template>
