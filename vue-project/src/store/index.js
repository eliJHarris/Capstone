// src/store/index.js
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: '',
    claims: null,
    role: null,          // 'student' | 'advisor'
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    authHeader: (s) => (s.token ? { Authorization: `Bearer ${s.token}` } : {}),
  },
  actions: {
    setRole(role) { this.role = role },
    setToken(token) { this.token = token },
    setClaims(c) { this.claims = c },
    logout() {
      this.token = ''
      this.claims = null
      this.role = null
    },
  },
})
