<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>仪表盘</h1>
      <p>Web 指纹识别系统概览</p>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <template v-else>
    <div class="card-grid">
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总扫描任务</div>
          <div class="stat-value">{{ scanStore.statistics?.total_tasks || 0 }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon success">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ scanStore.statistics?.completed_tasks || 0 }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon running">
          <el-icon><Loading /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">进行中</div>
          <div class="stat-value">{{ scanStore.statistics?.running_tasks || 0 }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Monitor /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">已扫描 URL</div>
          <div class="stat-value">{{ scanStore.statistics?.total_urls_scanned || 0 }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">检测技术</div>
          <div class="stat-value">{{ scanStore.statistics?.total_technologies_detected || 0 }}</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Grid /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">独立域名</div>
          <div class="stat-value">{{ scanStore.statistics?.unique_domains || 0 }}</div>
        </div>
      </div>
    </div>
    </template>

    <div class="dashboard-content">
      <el-card class="recent-tasks-card">
        <template #header>
          <div class="card-header">
            <span>最近扫描任务</span>
            <el-button link type="primary" @click="$router.push('/results')">
              查看全部
            </el-button>
          </div>
        </template>

        <el-table
          v-loading="isLoading"
          :data="recentTasks"
          :show-header="true"
          class="recent-table"
        >
          <el-table-column prop="name" label="任务名称" min-width="150">
            <template #default="{ row }">
              {{ row.name || row.task_id }}
            </template>
          </el-table-column>

          <el-table-column prop="total_urls" label="URL数" width="100" align="center" />

          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="progress" label="进度" width="150">
            <template #default="{ row }">
              <el-progress
                :percentage="row.progress || 0"
                :stroke-width="6"
                :color="getProgressColor(row.progress)"
              />
            </template>
          </el-table-column>

          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                @click="viewTask(row)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="!isLoading && recentTasks.length === 0" class="empty-state">
          <el-icon class="empty-icon"><Document /></el-icon>
          <p>暂无扫描任务</p>
          <el-button type="primary" @click="$router.push('/scan')">
            开始扫描
          </el-button>
        </div>
      </el-card>

      <el-card class="quick-actions-card">
        <template #header>
          <span>快速操作</span>
        </template>

        <div class="quick-actions">
          <el-button type="primary" size="large" @click="$router.push('/scan')">
            <el-icon><Search /></el-icon>
            开始新扫描
          </el-button>

          <el-button size="large" @click="$router.push('/rules')">
            <el-icon><Setting /></el-icon>
            管理规则
          </el-button>

          <el-button size="large" @click="$router.push('/results')">
            <el-icon><Document /></el-icon>
            查看结果
          </el-button>
        </div>

        <div class="system-info">
          <h4>系统信息</h4>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="版本">
              {{ systemInfo.version }}
            </el-descriptions-item>
            <el-descriptions-item label="规则数量">
              {{ systemInfo.rulesCount }}
            </el-descriptions-item>
            <el-descriptions-item label="运行时间">
              {{ systemInfo.uptime }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, CircleCheck, Loading, Monitor, Cpu, Grid, Search, Setting } from '@element-plus/icons-vue'
import { useScanStore, useRulesStore } from '@/store'
import { systemApi, type HealthResponse } from '@/api'

const router = useRouter()
const scanStore = useScanStore()
const rulesStore = useRulesStore()

const recentTasks = computed(() => scanStore.tasks.slice(0, 5))
const isLoading = ref(false)

const systemInfo = ref({
  version: '1.0.0',
  rulesCount: 0,
  uptime: '计算中...'
})

let uptimeInterval: ReturnType<typeof setInterval> | null = null
let refreshInterval: ReturnType<typeof setInterval> | null = null

async function fetchData() {
  isLoading.value = true
  try {
    await Promise.all([
      scanStore.fetchStatistics(),
      scanStore.fetchTasks({ limit: 5 }),
      rulesStore.fetchCount(),
      systemApi.health().then(res => {
        const data = res.data as HealthResponse
        systemInfo.value.version = data.version
        return data
      }).catch(() => null)
    ])

    systemInfo.value.rulesCount = rulesStore.totalCount
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    isLoading.value = false
  }
}

function startUptimeTimer() {
  const startTime = Date.now()
  uptimeInterval = setInterval(() => {
    const elapsed = Date.now() - startTime
    const hours = Math.floor(elapsed / 3600000)
    const minutes = Math.floor((elapsed % 3600000) / 60000)
    const seconds = Math.floor((elapsed % 60000) / 1000)
    systemInfo.value.uptime = `${hours}小时 ${minutes}分 ${seconds}秒`
  }, 1000)
}

function startAutoRefresh() {
  // Auto-refresh data every 5 seconds if there are running tasks
  refreshInterval = setInterval(async () => {
    try {
      await scanStore.fetchStatistics()
      await scanStore.fetchTasks({ limit: 5 })
    } catch (error) {
      console.error('Auto-refresh failed:', error)
    }
  }, 5000)
}

function getStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status: string): string {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

function getProgressColor(progress: number | undefined): string {
  if (!progress || progress < 30) return '#F56C6C'
  if (progress < 70) return '#E6A23C'
  return '#67C23A'
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function viewTask(task: any) {
  router.push(`/results/${task.task_id}`)
}

onMounted(() => {
  fetchData()
  startUptimeTimer()
  startAutoRefresh()
})

onUnmounted(() => {
  if (uptimeInterval) clearInterval(uptimeInterval)
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<style lang="scss" scoped>
.dashboard {
  .page-header {
    margin-bottom: 24px;

    h1 {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    p {
      color: var(--text-color-secondary);
    }
  }
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-color-secondary);

  .el-icon {
    margin-bottom: 12px;
    color: var(--accent-blue);
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;

  .stat-icon {
    font-size: 40px;
    color: var(--accent-blue);

    &.success {
      color: #67C23A;
    }

    &.running {
      color: #E6A23C;
      animation: rotate 2s linear infinite;
    }
  }

  .stat-content {
    flex: 1;

    .stat-label {
      font-size: 12px;
      color: var(--text-color-secondary);
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
    }
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.recent-table {
  :deep(.el-table__row) {
    cursor: pointer;
  }
}

.empty-state {
  text-align: center;
  padding: 40px;

  .empty-icon {
    font-size: 48px;
    color: var(--text-color-secondary);
    opacity: 0.5;
    margin-bottom: 12px;
  }

  p {
    margin-bottom: 16px;
    color: var(--text-color-secondary);
  }
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;

  .el-button {
    justify-content: flex-start;
    padding-left: 20px;

    .el-icon {
      margin-right: 8px;
    }
  }
}

.system-info {
  border-top: 1px solid var(--border-color);
  padding-top: 16px;

  h4 {
    font-size: 14px;
    margin-bottom: 12px;
  }
}
</style>
