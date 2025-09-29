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
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
