// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store'

const Login = () => import('@/components/LoginForm.vue')
const TestPage = () => import('@/views/TestPage.vue') // or /pages if you chose that

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: Login, meta: { public: true } },
    { path: '/test', component: TestPage, meta: { requiresAuth: true } },
  ],
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.meta.requiresAuth && !store.isLoggedIn) {
    return { path: '/login' }
  }
})

export default router
