import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue')
  },
  {
    path: '/scan',
    name: 'Scan',
    component: () => import('@/views/Scan.vue')
  },
  {
    path: '/rules',
    name: 'Rules',
    component: () => import('@/views/Rules.vue')
  },
  {
    path: '/results',
    name: 'Results',
    component: () => import('@/views/Results.vue')
  },
  {
    path: '/results/:id',
    name: 'ResultDetail',
    component: () => import('@/views/ResultDetail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
