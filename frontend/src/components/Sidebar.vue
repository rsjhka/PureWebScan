<template>
  <aside class="sidebar">
    <el-menu
      :default-active="activeMenu"
      :router="true"
      class="sidebar-menu"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <el-menu-item index="/scan">
        <el-icon><Search /></el-icon>
        <template #title>开始扫描</template>
      </el-menu-item>

      <el-menu-item index="/results">
        <el-icon><Document /></el-icon>
        <template #title>扫描结果</template>
      </el-menu-item>

      <el-menu-item index="/rules">
        <el-icon><Setting /></el-icon>
        <template #title>规则管理</template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <div class="version-info">
        <span class="version-label">版本</span>
        <span class="version-number">v1.0.0</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { HomeFilled, Search, Document, Setting } from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-color);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: background var(--transition-speed);
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 16px 12px;

  :deep(.el-menu-item) {
    height: 48px;
    line-height: 48px;
    margin-bottom: 4px;
    border-radius: 10px;
    padding-left: 16px !important;
    transition: all 0.2s ease;

    .el-icon {
      margin-right: 12px;
      font-size: 18px;
    }

    &.is-active {
      background: linear-gradient(135deg, rgba(135, 206, 235, 0.15), rgba(135, 206, 235, 0.05));
      color: var(--accent-blue);
      font-weight: 600;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 24px;
        background: var(--accent-blue);
        border-radius: 0 4px 4px 0;
      }
    }

    &:hover:not(.is-active) {
      background: var(--bg-color-secondary);
      color: var(--accent-blue);
    }
  }
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.version-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  .version-label {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-color-secondary);
    letter-spacing: 0.5px;
  }

  .version-number {
    font-size: 13px;
    color: var(--text-color);
    font-weight: 600;
  }
}
</style>
