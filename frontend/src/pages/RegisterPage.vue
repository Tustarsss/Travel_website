<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'

import PageSection from '../components/ui/PageSection.vue'
import ErrorAlert from '../components/ui/ErrorAlert.vue'
import SuccessAlert from '../components/ui/SuccessAlert.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  username: '',
  password: '',
  confirmPassword: '',
})

const submitting = ref(false)
const formError = ref<string | null>(null)
const successMessage = ref<string | null>(null)

const redirectTo = (route.query.redirect as string | undefined) ?? '/'

const handleSubmit = async () => {
  formError.value = null
  successMessage.value = null

  if (!form.email.trim() || !form.username.trim() || !form.password) {
    formError.value = '请填写邮箱、用户名和密码'
    return
  }

  if (form.password.length < 8) {
    formError.value = '密码长度至少需要 8 个字符'
    return
  }

  if (form.password !== form.confirmPassword) {
    formError.value = '两次输入的密码不一致'
    return
  }

  submitting.value = true

  try {
    await authStore.register({
      email: form.email.trim(),
      username: form.username.trim(),
      password: form.password,
    })

    successMessage.value = '注册成功，正在自动登录...'

    await authStore.login({ email: form.email.trim(), password: form.password })

    await router.push(redirectTo)
  } catch (error: any) {
    formError.value = error?.response?.data?.detail ?? authStore.error ?? '注册失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center">
    <PageSection
      title="创建新账号"
      description="注册后即可保存专属旅行日记，收藏路线并与朋友分享"
    >
      <div class="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <ErrorAlert v-if="formError" :message="formError" />
        <SuccessAlert v-if="successMessage" :message="successMessage" />

        <form class="space-y-5" @submit.prevent="handleSubmit">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">邮箱</label>
            <input
              v-model="form.email"
              type="email"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="请输入邮箱"
              autocomplete="email"
            />
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">用户名</label>
            <input
              v-model="form.username"
              type="text"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="请输入用户名"
              autocomplete="username"
            />
            <p class="text-xs text-slate-400">用户名将同时用作展示昵称，可在个人中心修改</p>
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">密码</label>
            <input
              v-model="form.password"
              type="password"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="设置密码"
              autocomplete="new-password"
            />
            <p class="text-xs text-slate-400">密码长度至少 8 个字符，建议包含数字和字母</p>
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">确认密码</label>
            <input
              v-model="form.confirmPassword"
              type="password"
              class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/10"
              placeholder="再次输入密码"
              autocomplete="new-password"
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
            <span v-else>注册</span>
          </button>
        </form>

        <div class="text-sm text-slate-500">
          已有账号？
          <RouterLink
            :to="{ name: 'login', query: { redirect: redirectTo !== '/' ? redirectTo : undefined } }"
            class="font-semibold text-primary hover:text-primary/80"
          >
            直接登录
          </RouterLink>
        </div>
      </div>
    </PageSection>
  </div>
</template>
