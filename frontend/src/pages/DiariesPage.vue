<script setup lang="ts">
import PageSection from '../components/ui/PageSection.vue'
</script>

<template>
  <div class="space-y-6">
    <PageSection
      title="旅游日记管理"
      description="在这里可以撰写、浏览和管理您的旅游日记。功能开发中，敬请期待。"
    >
      <div class="flex flex-col items-center justify-center gap-6 py-16">
        <div class="text-8xl">📝</div>
        <h3 class="text-2xl font-semibold text-slate-700">旅游日记功能</h3>
        <p class="max-w-md text-center text-slate-500">
          该功能正在开发中，将支持以下特性：
        </p>
        <ul class="max-w-md space-y-2 text-left text-slate-600">
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>撰写旅游日记，支持文字、图片和视频</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>浏览所有用户的旅游日记</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>按热度、评价和个人兴趣推荐日记</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>按目的地查询和全文检索</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>日记压缩存储</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="text-primary">✓</span>
            <span>AIGC自动生成旅游动画</span>
          </li>
        </ul>
        <div class="mt-4 rounded-lg bg-blue-50 px-6 py-3 text-sm text-blue-700">
          功能开发中，即将上线
        </div>
      </div>
    </PageSection>
  </div>
</template>
