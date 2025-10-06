// store/index.js
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userType: null,
  }),
  actions: {
    login(type) {
      this.isLoggedIn = true
      this.userType = type
    },
  },
})
