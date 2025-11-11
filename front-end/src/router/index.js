import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import TabView from '@/views/TabView.vue'
import NotificationView from '@/views/NotificationView.vue'
import LoginView from '@/views/LoginView.vue'


const routes = [
  { path: '/login', component: LoginView },
  { path: '/', component: LandingPage },
  { path: '/dashboard', component: TabView, props: { tabName: 'Dashboard' } },
  { path: '/', component: LandingPage },
  { path: '/dashboard', component: TabView, props: { tabName: 'Dashboard' } },
  { path: '/notifications', component: NotificationView, props: { tabName: 'Notifications' } },
  { path: '/student-list', component: TabView, props: { tabName: 'Student List' } },
  { path: '/class-history', component: TabView, props: { tabName: 'Class History' } },
  { path: '/security', component: TabView, props: { tabName: 'Security' } },
  { path: '/schedules', component: TabView, props: { tabName: 'Schedules / Appointments' } },
  { path: '/:catchAll(.*)', redirect: '/' } 
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
