import { createRouter, createWebHistory } from "vue-router";
import LoginView from "@/views/LoginView.vue";
import Dashboard from "@/views/Dashboard.vue";
import TabView from "@/views/TabView.vue";
import LandingPage from "@/views/LandingPage.vue";
import { getAuthToken } from "@/services/auth.js";

const routes = [
  { path: "/login", name: "login", component: LoginView },
  { path: "/", name: "home", component: LandingPage },

  // Main dashboard and sections
  { path: "/dashboard", name: "dashboard", component: Dashboard, meta: { requiresAuth: true } },
  { path: "/notifications", name: "notifications", component: TabView, props: { tabName: "Notifications" }, meta: { requiresAuth: true } },
  { path: "/student-list", name: "student-list", component: TabView, props: { tabName: "Student List" }, meta: { requiresAuth: true } },
  { path: "/class-history", name: "class-history", component: TabView, props: { tabName: "Class History" }, meta: { requiresAuth: true } },
  { path: "/security", name: "security", component: TabView, props: { tabName: "Security" }, meta: { requiresAuth: true } },
  { path: "/schedules", name: "schedules", component: TabView, props: { tabName: "Schedules / Appointments" }, meta: { requiresAuth: true } },

  { path: "/:catchAll(.*)", redirect: "/login" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Require login for any protected route
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth) {
    const token = getAuthToken();
    if (!token) {
      console.warn("🔒 Not authenticated, redirecting to login...");
      return next({ name: "login" });
    }
  }
  next();
});

export default router;
