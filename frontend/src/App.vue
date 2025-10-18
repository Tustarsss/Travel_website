<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAuthStore } from './stores/auth'

const navLinks = [
  { to: '/', label: '旅游推荐' },
  { to: '/routing', label: '路线规划' },
  { to: '/facilities', label: '场所查询' },
  { to: '/diaries', label: '旅游日记' },
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isAuthenticated, user } = storeToRefs(authStore)

const activePath = computed(() => route.path)
const displayName = computed(
  () => user.value?.username ?? '我的账户'
)

const showUserMenu = ref(false)

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const handleLogout = async () => {
  closeUserMenu()
  await authStore.logout()
  await router.push({ name: 'home' })
}

const goToProfile = async () => {
  closeUserMenu()
  await router.push({ name: 'profile' })
}

watch(
  () => route.fullPath,
  () => {
    closeUserMenu()
  }
)

void authStore.ensureProfile()
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
        <div class="flex items-center gap-4">
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

          <div v-if="isAuthenticated" class="relative">
            <button
              class="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-primary/60 hover:text-primary"
              @click="toggleUserMenu"
            >
              <span class="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                {{ displayName.charAt(0).toUpperCase() }}
              </span>
              <span class="hidden sm:inline">{{ displayName }}</span>
              <svg
                class="h-3 w-3 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <transition name="fade" mode="out-in">
              <div
                v-if="showUserMenu"
                class="absolute right-0 mt-2 w-44 rounded-xl border border-slate-200 bg-white p-2 text-sm shadow-xl"
              >
                <button
                  class="w-full rounded-lg px-3 py-2 text-left text-slate-600 hover:bg-slate-100 hover:text-primary"
                  @click="goToProfile"
                >
                  个人中心
                </button>
                <button
                  class="w-full rounded-lg px-3 py-2 text-left text-red-500 hover:bg-red-50"
                  @click="handleLogout"
                >
                  退出登录
                </button>
              </div>
            </transition>
          </div>

          <RouterLink
            v-else
            to="/login"
            class="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-primary/90"
          >
            登录 / 注册
          </RouterLink>
        </div>
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

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
