import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    sidebarOpen: true,
  }),
  actions: {
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    setSidebar(open) {
      this.sidebarOpen = Boolean(open)
    },
  },
})
