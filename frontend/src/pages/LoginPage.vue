<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'

import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  identifier: '',
  password: '',
})

const submitting = ref(false)
const formError = ref<string | null>(null)

const redirectTo = (route.query.redirect as string | undefined) ?? '/'

const handleSubmit = async () => {
  if (!form.identifier.trim() || !form.password) {
    formError.value = '请输入账号和密码'
    return
  }

  submitting.value = true
  formError.value = null

  try {
    await authStore.login({
      identifier: form.identifier.trim(),
      password: form.password,
    })
    await router.push(redirectTo)
  } catch (error: any) {
    formError.value = error?.response?.data?.detail ?? authStore.error ?? '登录失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center">
    <PageSection
      title="欢迎回来！"
      description="登录后即可撰写旅行日记、收藏路线并同步个人偏好"
    >
      <div class="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <ErrorAlert v-if="formError" :message="formError" />

        <form class="space-y-5" @submit.prevent="handleSubmit">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">用户名或邮箱</label>
            <input
              v-model="form.identifier"
              type="text"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="请输入用户名或邮箱"
              autocomplete="username"
            />
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">密码</label>
            <input
              v-model="form.password"
              type="password"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>

          <button
            type="submit"
            class="flex w-full items-center justify-center rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
            :disabled="submitting"
          >
            <svg
              v-if="submitting"
              class="h-5 w-5 animate-spin text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <span v-else>登录</span>
          </button>
        </form>

        <div class="text-sm text-slate-500">
          还没有账号？
          <RouterLink
            :to="{ name: 'register', query: { redirect: redirectTo !== '/' ? redirectTo : undefined } }"
            class="font-semibold text-primary hover:text-primary/80"
          >
            立即注册
          </RouterLink>
        </div>
      </div>
    </PageSection>
  </div>
</template>
