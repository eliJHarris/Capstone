import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DropView from '../views/DropView.vue'
import DashBoardView from '../views/DashBoardView.vue'

const routes = [
  { path: '/', component: LoginView },
  { path: '/drop', component: DropView },
  { path: '/dashboard', component: DashBoardView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
