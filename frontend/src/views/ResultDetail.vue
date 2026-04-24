<template>
  <div class="result-detail">
    <div class="page-header">
      <div class="header-content">
        <el-button link @click="$router.push('/results')">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <h1>扫描详情</h1>
      </div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="error" class="error-state">
      <el-alert :title="error" type="error" show-icon />
      <el-button @click="fetchData" type="primary">重试</el-button>
    </div>

    <div v-else-if="taskData" class="detail-content">
      <el-card class="info-card">
        <template #header>
          <span>任务信息</span>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ taskData.task_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(taskData.status)">
              {{ getStatusText(taskData.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="总URL数">{{ taskData.total_urls }}</el-descriptions-item>
          <el-descriptions-item label="已完成">{{ taskData.completed_urls }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(taskData.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="进度">
            <el-progress
              :percentage="Math.round(taskData.progress || 0)"
              :color="getProgressColor(taskData.progress)"
            />
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="actions-card">
        <el-button type="primary" @click="exportResults('json')">
          <el-icon><Download /></el-icon>
          导出 JSON
        </el-button>
        <el-button @click="exportResults('csv')">
          <el-icon><Download /></el-icon>
          导出 CSV
        </el-button>
        <el-button type="danger" @click="deleteTask">
          <el-icon><Delete /></el-icon>
          删除任务
        </el-button>
      </el-card>

      <el-card class="results-card">
        <template #header>
          <span>扫描结果 ({{ results.length }})</span>
        </template>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="概览" name="overview">
            <div class="results-grid">
              <div
                v-for="result in results"
                :key="result.id"
                class="result-item"
                @click="selectResult(result)"
              >
                <div class="result-url">
                  <a :href="result.url" target="_blank" @click.stop>{{ result.url || 'N/A' }}</a>
                </div>
                <div class="result-meta">
                  <el-tag size="small" :type="getStatusType(result.status_code)">
                    {{ result.status_code || 'N/A' }}
                  </el-tag>
                  <span class="tech-count">{{ result.technology_count || 0 }} 个技术</span>
                </div>
                <div class="result-techs" v-if="result.technologies && result.technologies.length > 0">
                  <el-tag
                    v-for="tech in result.technologies.slice(0, 3)"
                    :key="tech.name"
                    size="small"
                    type="info"
                  >
                    {{ tech.name }}
                  </el-tag>
                  <span v-if="result.technologies.length > 3" class="more-techs">
                    +{{ result.technologies.length - 3 }}
                  </span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="详情" name="detail">
            <ResultTable :task-id="taskId" />
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-dialog
        v-model="showDetailDialog"
        :title="selectedResult?.url || '详情'"
        width="900px"
        class="detail-dialog"
      >
        <div v-if="selectedResult" class="result-detail-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="URL" :span="2">
              <a :href="selectedResult.url" target="_blank">{{ selectedResult.url }}</a>
            </el-descriptions-item>
            <el-descriptions-item label="域名">{{ selectedResult.base_domain || 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="状态码">{{ selectedResult.status_code || 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="服务器">{{ selectedResult.server || 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="扫描耗时">{{ selectedResult.scan_duration || 0 }}ms</el-descriptions-item>
          </el-descriptions>

          <div class="tech-section">
            <h3>检测到的技术 ({{ selectedResult.technology_count || 0 }})</h3>
            <div class="tech-grid">
              <div
                v-for="tech in selectedResult.technologies"
                :key="tech.name"
                class="tech-card"
              >
                <div class="tech-header">
                  <span class="tech-name">{{ tech.name }}</span>
                  <el-tag size="small" type="info">{{ tech.slug }}</el-tag>
                </div>
                <div class="tech-info">
                  <span class="confidence">置信度: {{ tech.confidence }}%</span>
                  <span v-if="tech.version" class="version">版本: {{ tech.version }}</span>
                </div>
                <div v-if="tech.categories && tech.categories.length" class="tech-categories">
                  <el-tag
                    v-for="cat in tech.categories"
                    :key="cat.slug"
                    size="small"
                  >
                    {{ cat.name }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>

          <div v-if="selectedResult.headers" class="headers-section">
            <h3>响应头</h3>
            <pre class="headers-code">{{ JSON.stringify(selectedResult.headers, null, 2) }}</pre>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Loading, Download, Delete } from '@element-plus/icons-vue'
import { scanApi, resultApi, type ScanTask, type ScanResult } from '@/api'
import ResultTable from '@/components/ResultTable.vue'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => route.params.id as string)

const isLoading = ref(false)
const error = ref('')
const taskData = ref<ScanTask | null>(null)
const results = ref<ScanResult[]>([])
const activeTab = ref('overview')
const showDetailDialog = ref(false)
const selectedResult = ref<ScanResult | null>(null)
let pollIntervalId: number | null = null

const isTaskRunning = computed(() => {
  return taskData.value?.status === 'running' || taskData.value?.status === 'pending'
})

async function fetchData() {
  isLoading.value = true
  error.value = ''

  try {
    const [taskRes, resultsRes] = await Promise.all([
      scanApi.getTask(taskId.value),
      resultApi.list({ task_id: taskId.value, limit: 500 })
    ])

    taskData.value = taskRes.data
    results.value = resultsRes.data

    // Start/stop polling based on task status
    if (isTaskRunning.value) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (e: any) {
    const errorMsg = e.response?.data?.detail || e.message || '获取数据失败'
    error.value = errorMsg
    ElMessage.error(errorMsg)
  } finally {
    isLoading.value = false
  }
}

function startPolling() {
  if (pollIntervalId) return
  pollIntervalId = window.setInterval(async () => {
    try {
      const { data } = await scanApi.getTaskStatus(taskId.value)
      
      if (taskData.value) {
        taskData.value.status = data.status
        taskData.value.progress = data.progress
        taskData.value.completed_urls = data.completed_urls
      }

      // Stop polling if task completed
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        stopPolling()
        // Refresh full data
        await fetchData()
      }
    } catch (e) {
      console.error('Polling error:', e)
    }
  }, 2000)
}

function stopPolling() {
  if (pollIntervalId) {
    clearInterval(pollIntervalId)
    pollIntervalId = null
  }
}

function selectResult(result: ScanResult) {
  selectedResult.value = result
  showDetailDialog.value = true
}

async function exportResults(format: 'json' | 'csv') {
  try {
    const { data } = await resultApi.export(taskId.value, format)

    let content: string
    let mimeType: string

    if (format === 'json') {
      content = JSON.stringify(data.results || data, null, 2)
      mimeType = 'application/json'
    } else {
      content = data.data || ''
      mimeType = 'text/csv'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `scan-results-${taskId.value}.${format}`
    a.click()
    URL.revokeObjectURL(url)

    ElMessage.success(`导出成功: scan-results-${taskId.value}.${format}`)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function deleteTask() {
  try {
    await ElMessageBox.confirm('确定要删除此任务和所有结果吗？', '确认删除', {
      type: 'warning'
    })

    await scanApi.deleteTask(taskId.value)
    ElMessage.success('删除成功')
    router.push('/results')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getStatusType(status: string | number | undefined): string {
  if (typeof status === 'number') {
    if (status >= 200 && status < 300) return 'success'
    if (status >= 300 && status < 400) return 'warning'
    return 'danger'
  }

  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning'
  }
  return typeMap[status || ''] || 'info'
}

function getStatusText(status: string | undefined): string {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return textMap[status || ''] || status || ''
}

function getProgressColor(progress: number | undefined): string {
  if (!progress || progress < 30) return '#F56C6C'
  if (progress < 70) return '#E6A23C'
  return '#67C23A'
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchData()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.result-detail {
  .page-header {
    margin-bottom: 24px;

    .header-content {
      h1 {
        font-size: 24px;
        margin-top: 12px;
      }
    }
  }
}

.loading-state,
.error-state {
  text-align: center;
  padding: 60px;

  .el-icon {
    font-size: 32px;
    margin-bottom: 12px;
  }
}

.detail-content {
  .info-card {
    margin-bottom: 20px;
  }

  .actions-card {
    margin-bottom: 20px;
    display: flex;
    gap: 12px;
  }

  .results-card {
    margin-bottom: 20px;
  }
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.result-item {
  background: var(--bg-color-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
  }

  .result-url {
    margin-bottom: 8px;

    a {
      color: var(--accent-blue);
      text-decoration: none;
      word-break: break-all;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .result-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;

    .tech-count {
      font-size: 12px;
      color: var(--text-color-secondary);
    }
  }

  .result-techs {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;

    .more-techs {
      font-size: 12px;
      color: var(--text-color-secondary);
      padding: 2px 6px;
    }
  }
}

.result-detail-content {
  .tech-section {
    margin-top: 20px;

    h3 {
      margin-bottom: 12px;
    }
  }

  .tech-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .tech-card {
    background: var(--bg-color-secondary);
    border-radius: 6px;
    padding: 12px;

    .tech-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .tech-name {
        font-weight: 600;
      }
    }

    .tech-info {
      font-size: 12px;
      color: var(--text-color-secondary);
      margin-bottom: 8px;

      .confidence {
        margin-right: 12px;
      }
    }

    .tech-categories {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
  }

  .headers-section {
    margin-top: 20px;

    h3 {
      margin-bottom: 12px;
    }

    .headers-code {
      background: var(--bg-color-secondary);
      padding: 12px;
      border-radius: 6px;
      font-size: 12px;
      max-height: 300px;
      overflow: auto;
    }
  }
}
</style>
