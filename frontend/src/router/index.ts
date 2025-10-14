import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

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
      meta: { requiresAuth: true },
    },
    {
      path: '/diaries/:id',
      name: 'diary-detail',
      component: () => import('../pages/DiaryDetailPage.vue'),
      props: true,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../pages/RegisterPage.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../pages/ProfilePage.vue'),
      meta: { requiresAuth: true },
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

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  if (auth.accessToken && !auth.user) {
    await auth.ensureProfile()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({
      name: 'login',
      query: { redirect: to.fullPath !== '/' ? to.fullPath : undefined },
    })
    return
  }

  if (to.meta.requiresGuest && auth.isAuthenticated) {
    next((typeof to.query.redirect === 'string' && to.query.redirect) || '/')
    return
  }

  next()
})

export default router
