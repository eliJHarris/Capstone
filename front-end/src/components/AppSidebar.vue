<template>
  <v-navigation-drawer
    model-value="true"
    width="260"
    variant="permanent"
    class="pa-2"
    style="background-color:#ccccc6;"
  >
    <div class="pa-2">
      <v-avatar size="48" class="mb-2">
        <img src=/src/assets/mockup/Avatar.png style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />
      </v-avatar>
      <div class="subtitle-1 font-weight-medium">Jordan Casey</div>
      <div class="caption">{{ roleLabel }}</div>
    </div>

    <v-divider class="my-2" />

    <v-list nav>
      <v-list-item
        v-for="item in navItems"
        :key="item.title"
        :to="item.to"
        router
      >
        <v-list-item-title>{{ item.title }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script>
export default {
  name: 'AppSidebar',
  props: {
    role: { type: String, default: 'advisor' }
  },
  computed: {
    roleLabel() {
      return this.role === 'advisor' ? 'Advisor' : 'Student'
    },
    navItems() {
      if (this.role === 'advisor') {
        return [
        { title: 'Dashboard', to: '/dashboard' },
        { title: 'Notifications', to: '/notifications' },
        { title: 'Student List', to: '/student-list' },
        { title: 'Security', to: '/security' },
        { title: 'Schedules / Appointments', to: '/schedules' },
        { title: 'PDF Scraper', to: '/pdf-scraper' },
        { title: 'Degree Validation', to: '/degree-validation' },
        ]
      }
      return [
        { title: 'Dashboard', to: '/dashboard' },
        { title: 'Notifications', to: '/notifications' },
        { title: 'Class History', to: '/class-history' },
        { title: 'Security', to: '/security' },
        { title: 'Schedules / Appointments', to: '/schedules' },
        { title: 'PDF Scraper', to: '/pdf-scraper' },
        { title: 'Degree Validation', to: '/degree-validation' },
      ]
    },
  }
}
</script>
