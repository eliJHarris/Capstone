import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import LoginView from '@/views/LoginView.vue'
import DashboardLayout from '@/views/Dashboard.vue'
import DashboardHome from '@/views/DashboardHome.vue'
import PlaceholderView from '@/views/PlaceholderView.vue'
import SchedulesView from '@/views/SchedulesView.vue'
import PdfScraperView from '@/views/PdfScraperView.vue'
import DegreePlanValidationView from '@/views/DegreePlanValidationView.vue'

const dashboardChildren = [
  { path: 'dashboard', name: 'dashboard', component: DashboardHome },
  {
    path: 'notifications',
    name: 'notifications',
    component: PlaceholderView,
    props: { title: 'Notifications', description: 'Alerts from advisees and system events will appear here.' },
  },
  {
    path: 'student-list',
    name: 'student-list',
    component: PlaceholderView,
    props: { title: 'Student List', description: 'Manage advisees and their assigned advisors.' },
  },
  {
    path: 'class-history',
    name: 'class-history',
    component: PlaceholderView,
    props: { title: 'Class History', description: 'Historical enrollment data will be displayed here.' },
  },
  {
    path: 'security',
    name: 'security',
    component: PlaceholderView,
    props: { title: 'Security', description: 'Account security settings and audit trails.' },
  },
  { path: 'schedules', name: 'schedules', component: SchedulesView },
  { path: 'pdf-scraper', name: 'pdf-scraper', component: PdfScraperView },
  {
    path: 'degree-validation',
    name: 'degree-validation',
    component: DegreePlanValidationView,
  },
]

const routes = [
  { path: '/', name: 'landing', component: LandingPage },
  { path: '/login', name: 'login', component: LoginView },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true },
    children: dashboardChildren,
  },
  { path: '/:catchAll(.*)', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function isAuthenticated() {
  if (typeof window === 'undefined') return false
  return Boolean(window.localStorage.getItem('auth_token'))
}

router.beforeEach((to, from, next) => {
  const authed = isAuthenticated()
  const requiresAuth = to.matched.some((record) => record.meta?.requiresAuth)

  if (requiresAuth && !authed) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  if ((to.name === 'login' || to.name === 'landing') && authed) {
    return next({ path: '/dashboard' })
  }

  return next()
})

export default router
