<template>
  <div class="result-table">
    <div class="table-header">
      <div class="header-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索URL或域名..."
          clearable
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <div class="header-right">
        <el-select
          v-model="filterDomain"
          placeholder="按域名筛选"
          clearable
          @change="handleFilter"
          class="filter-select"
        >
          <el-option
            v-for="domain in domains"
            :key="domain"
            :label="domain"
            :value="domain"
          />
        </el-select>

        <el-button @click="refreshData" :loading="isLoading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-table
      :data="displayData"
      :loading="isLoading"
      stripe
      @row-click="handleRowClick"
      class="results-table"
    >
      <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <a :href="row.url" target="_blank" class="url-link" @click.stop>
            {{ row.url }}
          </a>
        </template>
      </el-table-column>

      <el-table-column prop="base_domain" label="域名" width="150" />

      <el-table-column prop="status_code" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag
            :type="getStatusType(row.status_code)"
            size="small"
          >
            {{ row.status_code || 'N/A' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="technology_count" label="技术数" width="80" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.technology_count || 0 }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="扫描时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            size="small"
            @click.stop="viewDetail(row)"
          >
            详情
          </el-button>
          <el-button
            type="danger"
            link
            size="small"
            @click.stop="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="totalCount > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalCount"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <div v-if="!isLoading && displayData.length === 0" class="empty-state">
      <el-icon class="empty-icon"><Document /></el-icon>
      <h3>暂无扫描结果</h3>
      <p>开始一次扫描来查看结果</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Document } from '@element-plus/icons-vue'
import { resultApi, type ScanResult } from '@/api'

const router = useRouter()

const props = defineProps<{
  taskId?: string
}>()

const results = ref<ScanResult[]>([])
const domains = ref<string[]>([])
const isLoading = ref(false)
const searchQuery = ref('')
const filterDomain = ref('')
const currentPage = ref(1)
const pageSize = 20

const filteredData = computed(() => {
  let data = results.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    data = data.filter(r =>
      (r.url && r.url.toLowerCase().includes(query)) ||
      (r.base_domain && r.base_domain.toLowerCase().includes(query))
    )
  }

  if (filterDomain.value) {
    data = data.filter(r => r.base_domain === filterDomain.value)
  }

  return data
})

const displayData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredData.value.slice(start, start + pageSize)
})

const totalCount = computed(() => filteredData.value.length)

// Debounce search to avoid excessive filtering
let searchTimeout: ReturnType<typeof setTimeout> | null = null

async function fetchResults() {
  // Prevent duplicate API calls
  if (isLoading.value) return

  isLoading.value = true
  try {
    const params: Record<string, any> = { limit: 500 }
    if (props.taskId) {
      params.task_id = props.taskId
    }
    const { data } = await resultApi.list(params)
    results.value = data

    const domainSet = new Set<string>()
    data.forEach((r: ScanResult) => {
      if (r.base_domain) {
        domainSet.add(r.base_domain)
      }
    })
    domains.value = Array.from(domainSet)

    // Reset pagination when data changes
    currentPage.value = 1
  } catch (error) {
    ElMessage.error('获取结果失败')
  } finally {
    isLoading.value = false
  }
}

async function handleDelete(row: ScanResult) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条扫描结果吗？',
      '确认删除',
      { type: 'warning' }
    )

    await resultApi.delete(row.id)
    results.value = results.value.filter(r => r.id !== row.id)
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function viewDetail(row: ScanResult) {
  router.push(`/results/${row.task_id}?url=${encodeURIComponent(row.url)}`)
}

function handleRowClick(row: ScanResult) {
  viewDetail(row)
}

function handleSearch() {
  // Debounce search input
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
  }, 300)
}

function handleFilter() {
  currentPage.value = 1
}

function handlePageChange(page: number) {
  currentPage.value = page
}

async function refreshData() {
  await fetchResults()
}

function getStatusType(code: number | null): string {
  if (!code) return 'info'
  if (code >= 200 && code < 300) return 'success'
  if (code >= 300 && code < 400) return 'warning'
  return 'danger'
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchResults()
})

// Only re-fetch when taskId changes, not on every render
watch(() => props.taskId, (newTaskId, oldTaskId) => {
  if (newTaskId !== oldTaskId) {
    fetchResults()
  }
})
</script>

<style lang="scss" scoped>
.result-table {
  background: var(--bg-color);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.header-left {
  flex: 1;
  max-width: 300px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 100%;
}

.filter-select {
  width: 180px;
}

.results-table {
  .url-link {
    color: var(--accent-blue);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;

  .empty-icon {
    font-size: 64px;
    color: var(--text-color-secondary);
    opacity: 0.5;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    margin-bottom: 8px;
    color: var(--text-color);
  }

  p {
    color: var(--text-color-secondary);
  }
}
</style>
