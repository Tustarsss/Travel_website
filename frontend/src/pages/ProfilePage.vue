<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'

import PageSection from '../components/ui/PageSection.vue'
import LoadingIndicator from '../components/ui/LoadingIndicator.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const { user, loading, error } = storeToRefs(authStore)
</script>

<template>
  <div class="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-10 py-10">
    <PageSection
      title="我的账户"
      description="查看个人信息，管理登录会话"
    >
      <div class="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <LoadingIndicator v-if="loading" class="mx-auto h-8 w-8" />
        <ErrorAlert v-else-if="error" :message="error" />
        <div v-else-if="user" class="space-y-6">
          <div>
            <h3 class="text-sm font-semibold uppercase tracking-wide text-primary">基础信息</h3>
            <dl class="mt-4 space-y-3 text-sm text-slate-600">
              <div class="grid grid-cols-1 gap-1 sm:grid-cols-3">
                <dt class="font-medium text-slate-500">用户名</dt>
                <dd class="sm:col-span-2">{{ user.username }}</dd>
              </div>
              <div class="grid grid-cols-1 gap-1 sm:grid-cols-3">
                <dt class="font-medium text-slate-500">昵称</dt>
                <dd class="sm:col-span-2">{{ user.display_name }}</dd>
              </div>
              <div class="grid grid-cols-1 gap-1 sm:grid-cols-3">
                <dt class="font-medium text-slate-500">邮箱</dt>
                <dd class="sm:col-span-2">{{ user.email }}</dd>
              </div>
              <div class="grid grid-cols-1 gap-1 sm:grid-cols-3">
                <dt class="font-medium text-slate-500">账户创建时间</dt>
                <dd class="sm:col-span-2">{{ new Date(user.created_at).toLocaleString() }}</dd>
              </div>
              <div class="grid grid-cols-1 gap-1 sm:grid-cols-3">
                <dt class="font-medium text-slate-500">最后更新</dt>
                <dd class="sm:col-span-2">{{ new Date(user.updated_at).toLocaleString() }}</dd>
              </div>
            </dl>
          </div>

          <div>
            <h3 class="text-sm font-semibold uppercase tracking-wide text-primary">登录状态</h3>
            <p class="mt-3 text-sm text-slate-500">
              您当前已登录，可以访问个性化功能。
            </p>
            <button
              type="button"
              class="mt-4 rounded-full border border-transparent bg-red-500 px-6 py-2 text-sm font-semibold text-white shadow transition hover:bg-red-600 focus:outline-none"
              @click="authStore.logout"
            >
              退出登录
            </button>
          </div>
        </div>
        <div v-else class="space-y-4 text-center text-sm text-slate-500">
          <p>当前未登录。</p>
          <RouterLink
            class="inline-flex items-center justify-center rounded-full bg-primary px-6 py-2 text-sm font-semibold text-white shadow transition hover:bg-primary/90"
            :to="{ name: 'login', query: { redirect: '/profile' } }"
          >
            前往登录
          </RouterLink>
        </div>
      </div>
    </PageSection>
  </div>
</template>
