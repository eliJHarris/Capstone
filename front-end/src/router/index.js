import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import LoginView from '@/views/LoginView.vue'
import DashboardLayout from '@/views/Dashboard.vue'
import DashboardHome from '@/views/DashboardHome.vue'
import PlaceholderView from '@/views/PlaceholderView.vue'
import SchedulesView from '@/views/SchedulesView.vue'
import PdfScraperView from '@/views/PdfScraperView.vue'

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
]

const routes = [
  { path: '/', name: 'landing', component: LandingPage },
  { path: '/login', name: 'login', component: LoginView },
  {
    path: '/',
    component: DashboardLayout,
    children: dashboardChildren,
  },
  { path: '/:catchAll(.*)', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
