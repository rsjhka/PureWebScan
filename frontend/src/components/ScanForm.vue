<template>
  <div class="scan-form">
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>扫描配置</span>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="任务名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="可选的任务名称"
            clearable
            :disabled="isProcessing"
          />
        </el-form-item>

        <el-form-item label="目标URL" prop="urls">
          <el-input
            v-model="formData.urls"
            type="textarea"
            :rows="8"
            placeholder="输入URL，每行一个&#10;例如：&#10;https://example.com"
            :disabled="isProcessing"
          />
        </el-form-item>

        <el-form-item label="扫描选项">
          <div class="options-grid">
            <div class="option-item">
              <span class="option-label">并发数</span>
              <el-slider
                v-model="formData.concurrent"
                :min="1"
                :max="100"
                :disabled="isProcessing"
                show-input
              />
            </div>

            <div class="option-item">
              <span class="option-label">超时时间</span>
              <el-slider
                v-model="formData.timeout"
                :min="5"
                :max="60"
                :disabled="isProcessing"
                show-input
              />
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button
              type="primary"
              :loading="isCreatingTask"
              :disabled="!canStartScan"
              @click="startScan"
              size="large"
            >
              <el-icon v-if="!isCreatingTask"><Upload /></el-icon>
              {{ isCreatingTask ? '创建中...' : '开始扫描' }}
            </el-button>

            <el-button
              @click="resetForm"
              :disabled="isProcessing"
              size="large"
            >
              重置
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="currentTask" class="progress-card">
      <template #header>
        <div class="card-header">
          <span>扫描进度</span>
          <el-button
            v-if="currentTask.status === 'running' || currentTask.status === 'pending'"
            type="danger"
            size="small"
            :loading="isCancelling"
            @click="cancelScan"
          >
            取消
          </el-button>
        </div>
      </template>

      <div class="progress-content">
        <el-progress
          type="dashboard"
          :percentage="Math.round(currentTask.progress || 0)"
          :color="progressColor"
        >
          <template #default>
            <div class="progress-info">
              <span class="progress-text">{{ getStatusText(currentTask.status) }}</span>
              <span class="progress-detail">
                {{ currentTask.completed_urls || 0 }} / {{ currentTask.total_urls || 0 }}
              </span>
            </div>
          </template>
        </el-progress>

        <div v-if="currentTask.status === 'completed'" class="result-link">
          <el-button type="primary" @click="viewResults">
            查看结果
          </el-button>
        </div>

        <div v-if="currentTask.status === 'failed'" class="error-info">
          <el-alert
            :title="currentTask.error_message || '扫描失败'"
            type="error"
            show-icon
            :closable="false"
          />
        </div>

        <div v-if="currentTask.status === 'cancelled'" class="cancelled-info">
          <el-alert
            title="扫描已取消"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>
      </div>
    </el-card>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      @close="errorMessage = ''"
      class="error-alert"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { scanApi } from '@/api'
import type { ScanTask } from '@/api'

const router = useRouter()

const formRef = ref<FormInstance>()
const formData = reactive({
  name: '',
  urls: '',
  concurrent: 50,
  timeout: 10
})

const rules: FormRules = {
  urls: [
    { required: true, message: '请输入至少一个URL', trigger: 'blur' }
  ]
}

// State management
const currentTask = ref<ScanTask | null>(null)
const errorMessage = ref('')
const isCreatingTask = ref(false)
const isCancelling = ref(false)
const isPolling = ref(false)
const pollIntervalId = ref<number | null>(null)

// Computed properties
const isProcessing = computed(() => isCreatingTask.value || isPolling.value)

const canStartScan = computed(() => {
  return formData.urls.trim().length > 0 && !isProcessing.value
})

const progressColor = computed(() => {
  const progress = currentTask.value?.progress ?? 0
  if (progress < 30) return '#F56C6C'
  if (progress < 70) return '#E6A23C'
  return '#67C23A'
})

function getStatusText(status: string | undefined): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '扫描中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status || ''] || status || ''
}

function parseUrls(): string[] {
  return formData.urls
    .split('\n')
    .map(url => url.trim())
    .filter(url => url.length > 0)
    .map(url => {
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return `https://${url}`
      }
      return url
    })
}

function stopPolling() {
  if (pollIntervalId.value) {
    clearInterval(pollIntervalId.value)
    pollIntervalId.value = null
  }
  isPolling.value = false
}

function startPolling(taskId: string) {
  stopPolling()
  isPolling.value = true

  pollIntervalId.value = window.setInterval(async () => {
    try {
      const { data } = await scanApi.getTaskStatus(taskId)

      // Update local state
      if (currentTask.value && currentTask.value.task_id === taskId) {
        currentTask.value.status = data.status
        currentTask.value.progress = data.progress
        currentTask.value.completed_urls = data.completed_urls
        currentTask.value.total_urls = data.total_urls
      }

      // Check if task completed
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        stopPolling()
        
        if (data.status === 'completed') {
          ElMessage.success('扫描完成！')
        }
      }
    } catch (error: any) {
      console.error('Polling error:', error)
      // Don't stop polling on error, just log it
    }
  }, 2000)
}

async function startScan() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const urls = parseUrls()
  if (urls.length === 0) {
    errorMessage.value = '请输入至少一个有效的URL'
    return
  }

  isCreatingTask.value = true
  errorMessage.value = ''

  try {
    const { data } = await scanApi.createTask({
      name: formData.name || undefined,
      urls,
      config: {
        concurrent: formData.concurrent,
        timeout: formData.timeout
      }
    })

    currentTask.value = data
    startPolling(data.task_id)

    ElMessage.success('扫描任务已创建')
  } catch (error: any) {
    errorMessage.value = error.message || '创建扫描任务失败'
    ElMessage.error(errorMessage.value)
  } finally {
    isCreatingTask.value = false
  }
}

async function cancelScan() {
  if (!currentTask.value) return

  const taskId = currentTask.value.task_id

  // Immediately update UI (optimistic update)
  isCancelling.value = true
  currentTask.value.status = 'cancelled'
  stopPolling()

  try {
    await scanApi.cancelTask(taskId)
    ElMessage.info('扫描已取消')
  } catch (error: any) {
    // Revert if API call fails
    currentTask.value.status = 'running'
    ElMessage.error(error.message || '取消扫描失败')
  } finally {
    isCancelling.value = false
  }
}

function viewResults() {
  if (currentTask.value) {
    router.push(`/results/${currentTask.value.task_id}`)
  }
}

function resetForm() {
  stopPolling()
  formData.name = ''
  formData.urls = ''
  formData.concurrent = 50
  formData.timeout = 10
  currentTask.value = null
  errorMessage.value = ''
  isCreatingTask.value = false
  isCancelling.value = false
}
</script>

<style lang="scss" scoped>
.scan-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-card,
.progress-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  width: 100%;
}

.option-item {
  .option-label {
    display: block;
    margin-bottom: 8px;
    font-size: 14px;
    color: var(--text-color-secondary);
  }

  .el-slider {
    margin: 0 12px;
  }
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.progress-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.progress-info {
  display: flex;
  flex-direction: column;
  align-items: center;

  .progress-text {
    font-size: 14px;
    color: var(--text-color-secondary);
  }

  .progress-detail {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-color);
  }
}

.result-link,
.error-info,
.cancelled-info {
  margin-top: 20px;
  width: 100%;
}

.error-alert {
  margin-top: 20px;
}
</style>
