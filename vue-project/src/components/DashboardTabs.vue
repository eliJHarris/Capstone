<template>
  <div>
    <button @click="selectTab('tab1')">Tab 1</button>
    <button @click="selectTab('tab2')">Tab 2</button>
    <p>Selected Tab: {{ currentTab }}</p>
  </div>
</template>

<script>
export default {
  name: 'DashboardTabs',
  data() {
    return { currentTab: 'tab1' }
  },
  methods: {
    selectTab(tab) {
      this.currentTab = tab
    },
  },
}
</script>
