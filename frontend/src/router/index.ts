import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../pages/HomePage.vue'),
    },
    {
      path: '/routing',
      name: 'routing',
      component: () => import('../pages/RoutingPage.vue'),
    },
    {
      path: '/facilities',
      name: 'facilities',
      component: () => import('../pages/FacilitiesPage.vue'),
    },
    {
      path: '/diaries',
      name: 'diaries',
      component: () => import('../pages/DiariesPage.vue'),
    },
    {
      path: '/diaries/new',
      name: 'diary-create',
      component: () => import('../pages/DiaryEditorPage.vue'),
    },
    {
      path: '/diaries/:id',
      name: 'diary-detail',
      component: () => import('../pages/DiaryDetailPage.vue'),
      props: true,
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
