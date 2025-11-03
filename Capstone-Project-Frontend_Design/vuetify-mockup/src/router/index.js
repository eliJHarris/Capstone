import { createRouter, createWebHistory } from "vue-router";
import LoginView from "@/views/LoginView.vue";
import DashboardView from "@/views/Dashboard.vue";
import { getAuthToken } from "@/services/auth.js";

const routes = [
  {
    path: "/login",
    name: "login",
    component: LoginView,
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: DashboardView,
    meta: { requiresAuth: true },
  },
  {
    path: "/",
    redirect: "/dashboard",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Global nav guard to block unauthenticated access
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth) {
    const token = getAuthToken();
    if (!token) {
      // no token? go to login
      return next({ name: "login" });
    }
  }
  next();
});

export default router;
