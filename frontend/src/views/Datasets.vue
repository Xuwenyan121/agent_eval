<template>
  <div class="datasets-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="search"
          placeholder="搜索数据集..."
          prefix-icon="Search"
          clearable
          style="width: 260px"
          @input="onSearch"
        />
        <el-select v-model="filterType" placeholder="数据类型" clearable style="width: 150px" @change="loadDatasets">
          <el-option label="问答对" value="qa" />
          <el-option label="图文" value="image_text" />
          <el-option label="端到端" value="e2e" />
          <el-option label="回归测试" value="regression" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 130px" @change="loadDatasets">
          <el-option label="草稿" value="draft" />
          <el-option label="已发布" value="published" />
          <el-option label="已归档" value="archived" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button class="btn-gradient" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建数据集
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="card" style="padding: 0; overflow: hidden">
      <el-table
        :data="filteredDatasets"
        v-loading="store.loading"
        @row-click="(row) => $router.push(`/datasets/${row.id}`)"
        class="dataset-table"
        :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
        empty-text=""
      >
        <el-table-column prop="name" label="数据集" min-width="200">
          <template #default="{ row }">
            <div class="ds-name">
              <span class="name-text">{{ row.name }}</span>
              <span class="name-desc" v-if="row.description">{{ truncate(row.description, 60) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="data_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="typeTagMap[row.data_type] || 'info'" effect="plain">
              {{ typeLabel(row.data_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="90" align="center">
          <template #default="{ row }">
            <span class="version-text">{{ row.version }}</span>
          </template>
        </el-table-column>
        <el-table-column label="样本数" width="90" align="center">
          <template #default="{ row }">
            <span class="sample-count">{{ row.sample_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="标签" width="160">
          <template #default="{ row }">
            <div class="tag-list" v-if="row.tags?.length">
              <el-tag v-for="tag in row.tags.slice(0, 3)" :key="tag" size="small" effect="plain" class="ds-tag">
                {{ tag }}
              </el-tag>
              <span v-if="row.tags.length > 3" class="more-tags">+{{ row.tags.length - 3 }}</span>
            </div>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button-group class="action-group">
              <el-button size="small" text @click.stop="$router.push(`/datasets/${row.id}`)">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click.stop="confirmDelete(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState
        v-if="!store.loading && filteredDatasets.length === 0"
        icon="FolderOpened"
        title="暂无数据集"
        description="创建第一个评测数据集以开始测试。"
        action-label="新建数据集"
        @action="showCreateDialog = true"
      />
    </div>

    <!-- Create Dataset Dialog -->
    <el-dialog v-model="showCreateDialog" title="新建数据集" width="520px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：客服问答数据集" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="数据类型" prop="data_type">
              <el-select v-model="createForm.data_type" style="width: 100%">
                <el-option label="问答对" value="qa" />
                <el-option label="图文" value="image_text" />
                <el-option label="端到端" value="e2e" />
                <el-option label="回归测试" value="regression" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="版本">
              <el-input v-model="createForm.version" placeholder="v1.0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="可选描述信息" />
        </el-form-item>
        <el-form-item label="标签（逗号分隔）">
          <el-input v-model="tagsInput" placeholder="例如：客服, FAQ, 生产环境" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button class="btn-gradient" :loading="store.loading" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Delete Confirm -->
    <ConfirmDialog
      v-model:visible="showDeleteDialog"
      title="删除数据集"
      :message="`确定删除数据集 '${deleteTarget?.name}' 吗？`"
      detail="该数据集中的所有样本将被永久删除。"
      confirm-label="删除"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useDatasetStore } from '@/stores/datasets'
import { formatDate, truncate, debounce } from '@/utils'
import { StatusBadge, EmptyState, ConfirmDialog } from '@/components'
import { ElMessage } from 'element-plus'

const store = useDatasetStore()
const search = ref('')
const filterType = ref('')
const filterStatus = ref('')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const createFormRef = ref(null)
const tagsInput = ref('')

const createForm = reactive({
  name: '',
  data_type: 'qa',
  version: 'v1.0',
  description: '',
  status: 'draft',
})

const createRules = {
  name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }],
  data_type: [{ required: true, message: '请选择数据类型', trigger: 'change' }],
}

const typeTagMap = { qa: 'primary', image_text: 'warning', e2e: 'success', regression: 'danger' }
const typeLabels = { qa: '问答对', image_text: '图文', e2e: '端到端', regression: '回归测试' }
const typeLabel = (t) => typeLabels[t] || t

const filteredDatasets = computed(() => {
  let list = store.datasets
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(d =>
      d.name?.toLowerCase().includes(q) ||
      d.description?.toLowerCase().includes(q)
    )
  }
  return list
})

const onSearch = debounce(() => {}, 300)

async function loadDatasets() {
  const params = {}
  if (filterType.value) params.data_type = filterType.value
  if (filterStatus.value) params.status = filterStatus.value
  await store.fetchDatasets(params)
}

async function handleCreate() {
  try {
    await createFormRef.value.validate()
  } catch { return }

  const tags = tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  const payload = { ...createForm, tags }

  try {
    await store.createDataset(payload)
    showCreateDialog.value = false
    // Reset form
    createForm.name = ''
    createForm.data_type = 'qa'
    createForm.version = 'v1.0'
    createForm.description = ''
    tagsInput.value = ''
    ElMessage.success('数据集创建成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '创建数据集失败')
  }
}

function confirmDelete(dataset) {
  deleteTarget.value = dataset
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  await store.deleteDataset(deleteTarget.value.id)
  showDeleteDialog.value = false
  deleteTarget.value = null
  ElMessage.success('数据集已删除')
}

onMounted(() => loadDatasets())
</script>

<style scoped>
.datasets-page { display: flex; flex-direction: column; gap: 16px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left { display: flex; gap: 10px; align-items: center; }

.dataset-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
  cursor: pointer;
}

.ds-name { display: flex; flex-direction: column; gap: 2px; }
.name-text { font-weight: 500; color: var(--text-primary); font-size: 13px; }
.name-desc { font-size: 11px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 280px; }

.version-text { color: #6C5CE7; font-weight: 600; font-size: 12px; }
.sample-count { color: var(--text-primary); font-weight: 600; }
.text-muted { color: var(--text-secondary); font-size: 12px; }

.tag-list { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.ds-tag { background: rgba(108, 92, 231, 0.1) !important; border-color: rgba(108, 92, 231, 0.3) !important; color: #6C5CE7 !important; }
.more-tags { font-size: 11px; color: var(--text-secondary); }

.action-group .el-button { color: var(--text-secondary); font-size: 14px; }
.action-group .el-button:hover { color: #6C5CE7; }
.action-group .el-button[type="danger"]:hover { color: #FF3D71; }
</style>
