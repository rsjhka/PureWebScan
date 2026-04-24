import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { scanApi, rulesApi, resultApi, type ScanTask, type ScanResult, type Statistics, type Rule, type Category } from '@/api'

export const useScanStore = defineStore('scan', () => {
  const tasks = ref<ScanTask[]>([])
  const currentTask = ref<ScanTask | null>(null)
  const statistics = ref<Statistics | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const recentTasks = computed(() => tasks.value.slice(0, 10))
  const runningTasks = computed(() => tasks.value.filter(t => t.status === 'running'))
  const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed'))

  async function fetchTasks(params?: { skip?: number; limit?: number; status?: string }) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await scanApi.listTasks(params)
      tasks.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch tasks'
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTask(taskId: string) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await scanApi.getTask(taskId)
      currentTask.value = data
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch task'
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function createTask(urls: string[], name?: string, config?: Record<string, any>) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await scanApi.createTask({ urls, name, config })
      tasks.value.unshift(data)
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to create task'
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function cancelTask(taskId: string) {
    try {
      await scanApi.cancelTask(taskId)
      const task = tasks.value.find(t => t.task_id === taskId)
      if (task) task.status = 'cancelled'
    } catch (e: any) {
      error.value = e.message || 'Failed to cancel task'
    }
  }

  async function deleteTask(taskId: string) {
    try {
      await scanApi.deleteTask(taskId)
      tasks.value = tasks.value.filter(t => t.task_id !== taskId)
    } catch (e: any) {
      error.value = e.message || 'Failed to delete task'
    }
  }

  async function fetchStatistics() {
    try {
      const { data } = await scanApi.getStatistics()
      statistics.value = data
    } catch (e: any) {
      console.error('Failed to fetch statistics:', e)
    }
  }

  let activePollInterval: ReturnType<typeof setInterval> | null = null

  async function pollTaskStatus(taskId: string, callback?: (status: any) => void) {
    // Stop any existing polling
    if (activePollInterval) {
      clearInterval(activePollInterval)
    }

    const poll = async () => {
      try {
        const { data } = await scanApi.getTaskStatus(taskId)
        const taskIndex = tasks.value.findIndex(t => t.task_id === taskId)
        if (taskIndex >= 0) {
          tasks.value[taskIndex].status = data.status
          tasks.value[taskIndex].progress = data.progress
          tasks.value[taskIndex].completed_urls = data.completed_urls
        }
        if (callback) callback(data)
        return data.status
      } catch {
        return null
      }
    }

    // Poll every 2 seconds
    activePollInterval = setInterval(async () => {
      const status = await poll()
      if (status === 'completed' || status === 'failed' || status === 'cancelled' || status === null) {
        if (activePollInterval) {
          clearInterval(activePollInterval)
          activePollInterval = null
        }
      }
    }, 2000)
  }

  function stopPolling() {
    if (activePollInterval) {
      clearInterval(activePollInterval)
      activePollInterval = null
    }
  }

  return {
    tasks,
    currentTask,
    statistics,
    isLoading,
    error,
    recentTasks,
    runningTasks,
    completedTasks,
    fetchTasks,
    fetchTask,
    createTask,
    cancelTask,
    deleteTask,
    fetchStatistics,
    pollTaskStatus,
    stopPolling
  }
})

export const useRulesStore = defineStore('rules', () => {
  const rules = ref<Rule[]>([])
  const categories = ref<Category[]>([])
  const totalCount = ref(0)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRules(params?: { skip?: number; limit?: number; category?: string; search?: string }) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await rulesApi.list(params)
      rules.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch rules'
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCategories() {
    try {
      const { data } = await rulesApi.getCategories()
      categories.value = data
    } catch (e: any) {
      console.error('Failed to fetch categories:', e)
    }
  }

  async function fetchCount() {
    try {
      const { data } = await rulesApi.getCount()
      totalCount.value = data.total_rules
    } catch (e: any) {
      console.error('Failed to fetch count:', e)
    }
  }

  async function uploadRules(files: File[]) {
    isLoading.value = true
    error.value = null
    try {
      await rulesApi.upload(files)
      await fetchCount()
    } catch (e: any) {
      error.value = e.message || 'Failed to upload rules'
    } finally {
      isLoading.value = false
    }
  }

  async function reloadRules() {
    isLoading.value = true
    error.value = null
    try {
      await rulesApi.reload()
      await fetchRules()
      await fetchCount()
    } catch (e: any) {
      error.value = e.message || 'Failed to reload rules'
    } finally {
      isLoading.value = false
    }
  }

  return {
    rules,
    categories,
    totalCount,
    isLoading,
    error,
    fetchRules,
    fetchCategories,
    fetchCount,
    uploadRules,
    reloadRules
  }
})

export const useResultsStore = defineStore('results', () => {
  const results = ref<ScanResult[]>([])
  const currentResult = ref<ScanResult | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchResults(params?: { skip?: number; limit?: number; task_id?: string; domain?: string }) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await resultApi.list(params)
      results.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch results'
    } finally {
      isLoading.value = false
    }
  }

  async function fetchResult(id: number) {
    isLoading.value = true
    error.value = null
    try {
      const { data } = await resultApi.get(id)
      currentResult.value = data
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch result'
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function deleteResult(id: number) {
    try {
      await resultApi.delete(id)
      results.value = results.value.filter(r => r.id !== id)
    } catch (e: any) {
      error.value = e.message || 'Failed to delete result'
    }
  }

  return {
    results,
    currentResult,
    isLoading,
    error,
    fetchResults,
    fetchResult,
    deleteResult
  }
})
