<template>
  <div class="app-container" :class="{ 'is-dark': isDark }">
    <Navbar />
    <div class="main-layout">
      <Sidebar />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDark } from '@vueuse/core'
import Navbar from './components/Navbar.vue'
import Sidebar from './components/Sidebar.vue'

const isDark = useDark()
</script>

<style lang="scss">
.app-container {
  min-height: 100vh;
  background: var(--bg-color);
  color: var(--text-color);
}

.main-layout {
  display: flex;
  min-height: calc(100vh - 60px);
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
