<template>
  <header class="navbar">
    <div class="navbar-left">
      <router-link to="/" class="logo">
        <el-icon class="logo-icon"><Monitor /></el-icon>
        <span class="logo-text">PureWebScan</span>
      </router-link>
    </div>

    <div class="navbar-right">
      <el-tooltip content="API文档" placement="bottom">
        <el-button link class="nav-btn" @click="openDocs">
          <el-icon><Document /></el-icon>
        </el-button>
      </el-tooltip>

      <el-tooltip :content="isDark ? '切换到亮色模式' : '切换到深色模式'" placement="bottom">
        <el-button link class="nav-btn" @click="toggleDark">
          <el-icon v-if="isDark"><Sunny /></el-icon>
          <el-icon v-else><Moon /></el-icon>
        </el-button>
      </el-tooltip>

      <div class="navbar-status">
        <span class="status-dot" :class="{ 'is-online': isOnline }"></span>
        <span class="status-text">{{ isOnline ? '在线' : '离线' }}</span>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useDark, useOnline } from '@vueuse/core'
import { Monitor, Document, Sunny, Moon } from '@element-plus/icons-vue'

const isDark = useDark()
const isOnline = useOnline()

function toggleDark() {
  isDark.value = !isDark.value
}

function openDocs() {
  window.open('/api/docs', '_blank')
}
</script>

<style lang="scss" scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: var(--navbar-height);
  padding: 0 24px;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-sm);
}

.navbar-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--text-color);
  font-size: 20px;
  font-weight: 700;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.8;
  }

  .logo-icon {
    font-size: 32px;
    color: var(--accent-blue);
    filter: drop-shadow(0 2px 4px rgba(135, 206, 235, 0.3));
  }

  .logo-text {
    background: linear-gradient(135deg, var(--text-color), var(--accent-blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;

  .nav-btn {
    font-size: 20px;
    color: var(--text-color-secondary);
    padding: 8px;
    border-radius: 8px;
    transition: all 0.2s;

    &:hover {
      color: var(--accent-blue);
      background: var(--bg-color-secondary);
    }
  }
}

.navbar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: var(--bg-color-secondary);
  border-radius: 20px;
  font-size: 13px;
  margin-left: 8px;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #94A3B8;
    transition: background 0.3s;

    &.is-online {
      background: #67C23A;
      box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
    }
  }

  .status-text {
    color: var(--text-color-secondary);
    font-weight: 500;
  }
}
</style>
