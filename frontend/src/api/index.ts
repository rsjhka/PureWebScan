import axios, { type AxiosResponse, type AxiosError } from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const message = error.response?.data?.detail
      || error.response?.data?.message
      || error.message
      || 'An unknown error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export interface ScanTask {
  id: number
  task_id: string
  name?: string
  urls: string[]
  total_urls: number
  completed_urls: number
  status: string
  status_text?: string
  progress: number
  error_message?: string
  config?: Record<string, unknown>
  created_at?: string
  started_at?: string
  completed_at?: string
}

export interface ScanResult {
  id: number
  task_id: string
  url: string
  base_domain?: string
  status_code?: number
  content_type?: string
  server?: string
  powered_by?: string
  technologies: Technology[]
  technology_count: number
  headers?: Record<string, string>
  cookies?: Record<string, string>
  error_message?: string
  scan_duration?: number
  created_at?: string
}

export interface Technology {
  name: string
  slug: string
  description?: string
  website?: string
  categories: Array<{ id: string; name: string; slug: string }>
  icons?: Record<string, unknown>
  confidence: number
  version?: string
}

export interface Category {
  id: string
  name: string
  slug: string
  count?: number
}

export interface HealthResponse {
  status: string
  version: string
  database_connected: boolean
  rules_loaded: number
  uptime: number
}

export interface Rule {
  name: string
  slug: string
  description?: string
  website?: string
  categories: Array<{ id: string; name: string; slug: string }>
  icons?: Record<string, unknown>
  confidence: number
  version?: string
  raw_rules?: Record<string, unknown>
}

export interface Statistics {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  running_tasks: number
  total_urls_scanned: number
  total_technologies_detected: number
  unique_domains: number
}

export interface TaskStatus {
  task_id: string
  status: string
  progress: number
  completed_urls: number
  total_urls: number
  status_text?: string
}

export interface ExportResponse {
  task_id?: string
  total_results?: number
  results?: ScanResult[]
  format?: string
  data?: string
}

export const scanApi = {
  createTask: (data: { name?: string; urls: string[]; config?: Record<string, unknown> }) =>
    api.post<ScanTask>('/tasks/', data),

  listTasks: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get<ScanTask[]>('/tasks/', { params }),

  getTask: (taskId: string) =>
    api.get<ScanTask>(`/tasks/${taskId}`),

  getTaskStatus: (taskId: string) =>
    api.get<{ task_id: string; status: string; progress: number; completed_urls: number; total_urls: number }>(`/tasks/${taskId}/status`),

  cancelTask: (taskId: string) =>
    api.post(`/tasks/${taskId}/cancel`),

  deleteTask: (taskId: string) =>
    api.delete(`/tasks/${taskId}`),

  getStatistics: () =>
    api.get<Statistics>('/tasks/statistics/summary')
}

export const rulesApi = {
  list: (params?: { skip?: number; limit?: number; category?: string; search?: string }) =>
    api.get<Rule[]>('/rules/', { params }),

  getCategories: () =>
    api.get<Category[]>('/rules/categories'),

  getRule: (name: string) =>
    api.get<Rule>(`/rules/${encodeURIComponent(name)}`),

  upload: (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return api.post('/rules/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  reload: () =>
    api.post('/rules/reload'),

  deleteRule: (name: string) =>
    api.delete(`/rules/${encodeURIComponent(name)}`),

  getCount: () =>
    api.get<{ total_rules: number; categories_count: number }>('/rules/stats/count')
}

export const resultApi = {
  list: (params?: { skip?: number; limit?: number; task_id?: string; domain?: string }) =>
    api.get<ScanResult[]>('/results/', { params }),

  get: (id: number) =>
    api.get<ScanResult>(`/results/${id}`),

  getByUrl: (url: string) =>
    api.get<ScanResult>(`/results/by-url/${encodeURIComponent(url)}`),

  delete: (id: number) =>
    api.delete(`/results/${id}`),

  listTechnologies: (params?: { skip?: number; limit?: number; category?: string }) =>
    api.get('/results/technologies/list', { params }),

  getTechnology: (name: string) =>
    api.get(`/results/technologies/${encodeURIComponent(name)}`),

  listDomains: (params?: { skip?: number; limit?: number }) =>
    api.get('/results/domains/list', { params }),

  export: (taskId: string, format: 'json' | 'csv' = 'json') =>
    api.get(`/results/export/${taskId}`, { params: { format } })
}

export const systemApi = {
  health: () =>
    api.get('/health')
}

export default api
