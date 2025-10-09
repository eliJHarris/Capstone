import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userType: null,
    selectedTab: 'home',
  }),
  actions: {
    login(type) {
      this.isLoggedIn = true
      this.userType = type
    },
    logout() {
      this.isLoggedIn = false
      this.userType = null
    },
  },
})

