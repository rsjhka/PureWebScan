<template>
  <div class="rule-list">
    <div class="list-header">
      <div class="header-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索规则..."
          clearable
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="filterCategory"
          placeholder="按分类筛选"
          clearable
          @change="handleFilter"
          class="category-select"
        >
          <el-option
            v-for="cat in categories"
            :key="cat.slug"
            :label="cat.name"
            :value="cat.slug"
          />
        </el-select>
      </div>

      <div class="header-right">
        <el-button @click="reloadRules" :loading="isLoading">
          <el-icon><Refresh /></el-icon>
          重新加载
        </el-button>

        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传规则
        </el-button>
      </div>
    </div>

    <el-table
      :data="displayData"
      :loading="isLoading"
      stripe
      class="rules-table"
    >
      <el-table-column prop="name" label="技术名称" min-width="150">
        <template #default="{ row }">
          <div class="tech-name">
            <span>{{ row.name }}</span>
            <el-tag size="small" type="info">{{ row.slug }}</el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />

      <el-table-column prop="categories" label="分类" width="200">
        <template #default="{ row }">
          <div class="category-tags">
            <el-tag
              v-for="cat in row.categories.slice(0, 2)"
              :key="cat.slug"
              size="small"
              class="category-tag"
            >
              {{ cat.name }}
            </el-tag>
            <span v-if="row.categories.length > 2" class="more-categories">
              +{{ row.categories.length - 2 }}
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="confidence" label="置信度" width="100" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="row.confidence || 100"
            :color="getConfidenceColor(row.confidence)"
            :stroke-width="6"
          />
        </template>
      </el-table-column>

      <el-table-column prop="version" label="版本" width="100">
        <template #default="{ row }">
          {{ row.version || '-' }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            size="small"
            @click="viewDetail(row)"
          >
            详情
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

    <el-dialog
      v-model="showUploadDialog"
      title="上传规则文件"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="10"
        :on-change="handleFileChange"
        :file-list="fileList"
        accept=".json,.yml,.yaml"
        drag
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="upload-tip">
            支持 .json, .yml, .yaml 格式
          </div>
        </template>
      </el-upload>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="isUploading">
          上传
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showDetailDialog"
      :title="selectedRule?.name || '规则详情'"
      width="700px"
    >
      <div v-if="selectedRule" class="rule-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ selectedRule.name }}</el-descriptions-item>
          <el-descriptions-item label="标识">{{ selectedRule.slug }}</el-descriptions-item>
          <el-descriptions-item label="分类" :span="2">
            {{ selectedRule.categories.map((c: any) => c.name).join(', ') }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ selectedRule.description || '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="网站">
            <a v-if="selectedRule.website" :href="selectedRule.website" target="_blank">
              {{ selectedRule.website }}
            </a>
            <span v-else>无</span>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ selectedRule.confidence || 100 }}%
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedRule.raw_rules" class="raw-rules">
          <h4>检测规则</h4>
          <el-tabs>
            <el-tab-pane
              v-for="(patterns, key) in rawRuleCategories"
              :key="key"
              :label="key"
              :name="key"
            >
              <pre class="rule-code">{{ JSON.stringify(patterns, null, 2) }}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Upload } from '@element-plus/icons-vue'
import { rulesApi, type Rule, type Category } from '@/api'

const rules = ref<Rule[]>([])
const categories = ref<Category[]>([])
const isLoading = ref(false)
const isUploading = ref(false)
const searchQuery = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const pageSize = 20
const showUploadDialog = ref(false)
const showDetailDialog = ref(false)
const selectedRule = ref<any>(null)
const fileList = ref<any[]>([])
const uploadFiles = ref<File[]>([])

const filteredData = computed(() => {
  let data = rules.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    data = data.filter(r =>
      r.name.toLowerCase().includes(query) ||
      (r.description && r.description.toLowerCase().includes(query)) ||
      r.slug.toLowerCase().includes(query)
    )
  }

  if (filterCategory.value) {
    data = data.filter(r =>
      r.categories.some((c: Category) => c.slug === filterCategory.value)
    )
  }

  return data
})

const displayData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredData.value.slice(start, start + pageSize)
})

const totalCount = computed(() => filteredData.value.length)

const rawRuleCategories = computed(() => {
  if (!selectedRule.value?.raw_rules) return {}

  const raw = selectedRule.value.raw_rules
  const categories: Record<string, any> = {}

  const relevantFields = ['headers', 'cookies', 'scripts', 'scriptSrc', 'meta', 'url', 'dom', 'implies']

  for (const field of relevantFields) {
    if (raw[field]) {
      categories[field] = raw[field]
    }
  }

  return categories
})

async function fetchRules() {
  isLoading.value = true
  try {
    const { data } = await rulesApi.list({ limit: 500 })
    rules.value = data
  } catch (error) {
    ElMessage.error('获取规则失败')
  } finally {
    isLoading.value = false
  }
}

async function fetchCategories() {
  try {
    const { data } = await rulesApi.getCategories()
    categories.value = data
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

async function reloadRules() {
  isLoading.value = true
  try {
    await rulesApi.reload()
    await fetchRules()
    ElMessage.success('规则已重新加载')
  } catch (error) {
    ElMessage.error('重新加载规则失败')
  } finally {
    isLoading.value = false
  }
}

function handleFileChange(_file: unknown, files: unknown[]) {
  fileList.value = files as any[]
  uploadFiles.value = (files as any[]).map((f: any) => f.raw)
}

async function handleUpload() {
  if (uploadFiles.value.length === 0) {
    ElMessage.warning('请选择至少一个规则文件')
    return
  }

  isUploading.value = true
  try {
    await rulesApi.upload(uploadFiles.value)
    ElMessage.success('规则文件上传成功')
    showUploadDialog.value = false
    fileList.value = []
    uploadFiles.value = []
    await fetchRules()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  } finally {
    isUploading.value = false
  }
}

function viewDetail(rule: Rule) {
  selectedRule.value = rule
  showDetailDialog.value = true
}

function handleSearch() {
  currentPage.value = 1
}

function handleFilter() {
  currentPage.value = 1
}

function handlePageChange(page: number) {
  currentPage.value = page
}

function getConfidenceColor(confidence: number | undefined): string {
  if (!confidence || confidence >= 80) return '#67C23A'
  if (confidence >= 50) return '#E6A23C'
  return '#F56C6C'
}

onMounted(() => {
  fetchRules()
  fetchCategories()
})
</script>

<style lang="scss" scoped>
.rule-list {
  background: var(--bg-color);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.header-left {
  display: flex;
  gap: 12px;
  flex: 1;
}

.search-input {
  width: 200px;
}

.category-select {
  width: 180px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.tech-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.category-tag {
  margin-right: 4px;
}

.more-categories {
  font-size: 12px;
  color: var(--text-color-secondary);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.upload-icon {
  font-size: 67px;
  color: var(--text-color-secondary);
  margin-bottom: 16px;
}

.upload-text {
  color: var(--text-color-secondary);

  em {
    color: var(--accent-blue);
    font-style: normal;
  }
}

.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.rule-detail {
  .raw-rules {
    margin-top: 20px;

    h4 {
      margin-bottom: 12px;
    }

    .rule-code {
      background: var(--bg-color-secondary);
      padding: 12px;
      border-radius: 4px;
      font-size: 12px;
      overflow-x: auto;
      max-height: 300px;
    }
  }
}
</style>
