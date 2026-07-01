<template>
  <div class="dataset-detail-page">
    <!-- Header -->
    <div class="page-header">
      <el-button text @click="$router.push('/datasets')" style="color: var(--text-secondary)">
        <el-icon><ArrowLeft /></el-icon>
        返回数据集
      </el-button>
      <div class="header-actions" v-if="dataset">
        <el-button size="small" @click="showVersionDialog = true">
          <el-icon><CopyDocument /></el-icon>
          新建版本
        </el-button>
        <el-button size="small" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
        <el-button size="small" class="btn-gradient" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加样本
        </el-button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else-if="dataset">
      <!-- Info Card -->
      <div class="card info-card">
        <div class="info-header">
          <div>
            <h3 class="ds-name">{{ dataset.name }}</h3>
            <p class="ds-desc" v-if="dataset.description">{{ dataset.description }}</p>
          </div>
          <StatusBadge :status="dataset.status" size="large" />
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">类型</span>
            <el-tag size="small" :type="typeTagMap[dataset.data_type]" effect="plain">{{ typeLabel(dataset.data_type) }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">版本</span>
            <span class="info-value accent">{{ dataset.version }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">样本数</span>
            <span class="info-value">{{ dataset.sample_count || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDate(dataset.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">更新时间</span>
            <span class="info-value">{{ formatDate(dataset.updated_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">标签</span>
            <div class="tag-list" v-if="dataset.tags?.length">
              <el-tag v-for="tag in dataset.tags" :key="tag" size="small" class="ds-tag">{{ tag }}</el-tag>
            </div>
            <span v-else class="info-value" style="color: var(--text-secondary)">—</span>
          </div>
        </div>
      </div>

      <!-- Samples Table -->
      <div class="card" style="padding: 0; overflow: hidden">
        <div class="samples-toolbar">
          <h4 style="margin: 0; color: var(--text-primary); font-size: 14px">
            样本
            <span class="sample-badge" v-if="dataset.sample_count">{{ dataset.sample_count }}</span>
          </h4>
          <el-input
            v-model="sampleSearch"
            placeholder="搜索 sample_id..."
            size="small"
            clearable
            style="width: 200px"
          />
        </div>

        <el-table
          :data="displaySamples"
          v-loading="samplesLoading"
          class="sample-table"
          :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
          empty-text=""
        >
          <el-table-column prop="sample_id" label="样本 ID" width="120">
            <template #default="{ row }">
              <span class="sample-id">{{ row.sample_id || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="input" label="输入" min-width="180">
            <template #default="{ row }">
              <span class="cell-text" v-html="highlightJson(row.input)"></span>
            </template>
          </el-table-column>
          <el-table-column prop="expected_output" label="期望输出" min-width="180">
            <template #default="{ row }">
              <span class="cell-text" v-html="highlightJson(row.expected_output)"></span>
            </template>
          </el-table-column>
          <el-table-column label="期望 Meta" width="160">
            <template #default="{ row }">
              <el-tag v-if="row.expected_meta && Object.keys(row.expected_meta).length" size="small" type="success" effect="plain">
                {{ Object.keys(row.expected_meta).length }} 个字段
              </el-tag>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="上下文" width="160">
            <template #default="{ row }">
              <span class="cell-text muted" v-if="row.context">{{ truncate(JSON.stringify(row.context), 80) }}</span>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="120">
            <template #default="{ row }">
              <el-tag v-for="tag in (row.tags || []).slice(0,2)" :key="tag" size="small" class="ds-tag">{{ tag }}</el-tag>
              <span v-if="!row.tags?.length" class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              <span class="text-muted">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click.stop="openEditDialog(row)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click.stop="confirmDeleteSample(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <EmptyState
          v-if="!samplesLoading && displaySamples.length === 0"
          icon="Document"
          title="暂无样本"
          description="请手动添加样本或上传 JSONL/CSV/XLSX 文件。"
        />

        <!-- Pagination -->
        <div class="pagination-wrap" v-if="totalPages > 1">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="dataset.sample_count || 0"
            layout="prev, pager, next"
            background
            @current-change="loadSamples"
          />
        </div>
      </div>
    </template>

    <!-- Add Sample Dialog -->
    <el-dialog v-model="showAddDialog" title="添加样本" width="560px">
      <el-form :model="sampleForm" label-position="top">
        <el-form-item label="样本 ID">
          <el-input v-model="sampleForm.sample_id" placeholder="可选，留空自动生成" />
        </el-form-item>
        <el-form-item label="输入（JSON）" :error="inputError">
          <el-input v-model="sampleForm.input" type="textarea" :rows="3" placeholder='{"query": "退货政策是什么？"}' />
        </el-form-item>
        <el-form-item label="期望输出（JSON 或纯文本）">
          <el-input v-model="sampleForm.expected_output" type="textarea" :rows="3" placeholder='{"answer": "30天内全额退款"}' />
        </el-form-item>
        <el-form-item label="上下文（JSON）">
          <el-input v-model="sampleForm.context" type="textarea" :rows="2" placeholder="可选的上下文信息" />
        </el-form-item>
        <el-form-item label="期望 Meta（JSON）">
          <el-input v-model="sampleForm.expected_meta" type="textarea" :rows="2" placeholder='可选，例如 {"agentId": "72d2ab...", "title_contains": "华为"}' />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="sampleForm.notes" placeholder="内部备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button class="btn-gradient" @click="handleAddSample">添加</el-button>
      </template>
    </el-dialog>

    <!-- Edit Sample Dialog -->
    <el-dialog v-model="showEditDialog" title="编辑样本" width="600px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="样本 ID">
          <el-input v-model="editForm.sample_id" disabled />
        </el-form-item>
        <el-form-item label="输入（JSON）" :error="editInputError">
          <el-input v-model="editForm.input" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="期望输出（JSON 或纯文本）">
          <el-input v-model="editForm.expected_output" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="期望 Meta（JSON）" help='SSE meta 字段验证，例如 {"agentId": "72d2ab...", "title_contains": "华为"}'>
          <el-input v-model="editForm.expected_meta" type="textarea" :rows="3" placeholder='{"agentId": "72d2abe16e32424aac127cef38a2aaf7"}' />
        </el-form-item>
        <el-form-item label="上下文（JSON）">
          <el-input v-model="editForm.context" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="editForm.tags_raw" placeholder="逗号分隔，例如: 企业查询,工商信息" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" placeholder="内部备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button class="btn-gradient" :loading="editSaving" @click="handleSaveSample">保存</el-button>
      </template>
    </el-dialog>

    <!-- Upload File Dialog (JSONL / CSV / XLSX) -->
    <el-dialog v-model="showUploadDialog" title="上传数据集文件" width="540px">
      <div class="upload-area">
        <p class="upload-hint">
          支持上传以下格式的文件：
        </p>
        <el-tabs v-model="uploadFormat" class="upload-tabs">
          <el-tab-pane label="JSONL" name="jsonl">
            <div class="format-desc">
              每行为一个 JSON 对象，包含字段：<code>sample_id</code>、<code>input</code>、<code>expected_output</code>、<code>context</code>
            </div>
          </el-tab-pane>
          <el-tab-pane label="CSV / XLSX" name="xlsx">
            <div class="format-desc">
              表格列自动映射规则：
              <ul>
                <li><code>convId</code> + <code>userId</code> + <code>content</code> → <strong>input</strong> JSON</li>
                <li><code>expected_output</code> + <code>toolcalling</code> → <strong>expected_output</strong> JSON</li>
                <li><code>toolcalling</code> 列为预期触发的 Agent 技能标识</li>
              </ul>
            </div>
          </el-tab-pane>
        </el-tabs>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".jsonl,.json,.csv,.xlsx,.xls"
          drag
          :on-change="onFileChange"
          :on-remove="() => (uploadFile = null)"
        >
          <el-icon style="font-size: 40px; color: #6C5CE7"><Upload /></el-icon>
          <div class="el-upload__text">拖拽文件到此处或<em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 .jsonl、.csv、.xlsx 格式</div>
          </template>
        </el-upload>
        <div v-if="uploadPreview" class="upload-preview">
          <el-icon><Document /></el-icon>
          <span>{{ uploadPreview }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button class="btn-gradient" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- Version Dialog -->
    <el-dialog v-model="showVersionDialog" title="创建新版本" width="400px">
      <el-form label-position="top">
        <el-form-item label="新版本号">
          <el-input v-model="newVersion" placeholder="例如 v2.0" />
        </el-form-item>
        <el-form-item label="复制样本">
          <el-switch v-model="copySamples" />
          <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px">将现有样本复制到新版本</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVersionDialog = false">取消</el-button>
        <el-button class="btn-gradient" :loading="store.loading" @click="handleCreateVersion">创建</el-button>
      </template>
    </el-dialog>

    <!-- Delete Sample Confirm -->
    <ConfirmDialog
      v-model:visible="showDeleteSampleDialog"
      title="删除样本"
      message="确定删除该样本吗？"
      detail="此操作不可撤销。"
      confirm-label="删除"
      @confirm="handleDeleteSample"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/datasets'
import { formatDate, truncate } from '@/utils'
import { StatusBadge, EmptyState, ConfirmDialog } from '@/components'
import { ElMessage } from 'element-plus'
import { Edit, Document } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const store = useDatasetStore()

const datasetId = route.params.id
const loading = ref(true)
const samplesLoading = ref(false)
const currentPage = ref(1)
const pageSize = 20
const sampleSearch = ref('')

const typeTagMap = { qa: 'primary', image_text: 'warning', e2e: 'success', regression: 'danger' }
const typeLabels = { qa: '问答对', image_text: '图文', e2e: '端到端', regression: '回归测试' }
const typeLabel = (t) => typeLabels[t] || t

const dataset = computed(() => store.currentDataset)
const totalPages = computed(() => Math.ceil((dataset.value?.sample_count || 0) / pageSize))

const displaySamples = computed(() => {
  if (!sampleSearch.value) return store.samples
  const q = sampleSearch.value.toLowerCase()
  return store.samples.filter(s => s.sample_id?.toLowerCase().includes(q))
})

function highlightJson(val) {
  if (!val) return '—'
  const str = typeof val === 'string' ? val : JSON.stringify(val)
  return truncate(str, 120).replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

async function loadDataset() {
  loading.value = true
  try {
    await store.fetchDataset(datasetId)
  } catch {
    ElMessage.error('加载数据集失败')
    router.push('/datasets')
  } finally {
    loading.value = false
  }
}

async function loadSamples() {
  samplesLoading.value = true
  await store.fetchSamples(datasetId, { page: currentPage.value, page_size: pageSize })
  samplesLoading.value = false
}

// Add Sample
const showAddDialog = ref(false)
const sampleForm = reactive({ sample_id: '', input: '', expected_output: '', expected_meta: '', context: '', notes: '' })
const inputError = ref('')
const outputError = ref('')

function parseJsonField(str, fieldName) {
  if (!str.trim()) return {}
  try {
    return JSON.parse(str)
  } catch {
    return null
  }
}

async function handleAddSample() {
  inputError.value = ''
  outputError.value = ''

  let input
  let expectedOutput
  try {
    input = sampleForm.input.trim() ? JSON.parse(sampleForm.input) : {}
  } catch { inputError.value = '输入 JSON 格式无效'; return }
  // expected_output: try JSON parse, fallback to plain text
  if (sampleForm.expected_output.trim()) {
    try {
      expectedOutput = JSON.parse(sampleForm.expected_output)
    } catch {
      expectedOutput = sampleForm.expected_output.trim()
    }
  } else {
    expectedOutput = ''
  }

  let context = null
  if (sampleForm.context.trim()) {
    try { context = JSON.parse(sampleForm.context) } catch { context = sampleForm.context }
  }

  const payload = {
    sample_id: sampleForm.sample_id || undefined,
    input,
    expected_output: expectedOutput,
    context,
    notes: sampleForm.notes,
  }
  // Parse expected_meta (optional)
  if (sampleForm.expected_meta.trim()) {
    try {
      payload.expected_meta = JSON.parse(sampleForm.expected_meta)
    } catch {
      inputError.value = '期望 Meta JSON 格式无效'; return
    }
  }

  try {
    await store.addSample(datasetId, payload)
    showAddDialog.value = false
    sampleForm.sample_id = ''
    sampleForm.input = ''
    sampleForm.expected_output = ''
    sampleForm.expected_meta = ''
    sampleForm.context = ''
    sampleForm.notes = ''
    ElMessage.success('样本添加成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '添加样本失败')
  }
}

// Upload File (JSONL / CSV / XLSX)
const showUploadDialog = ref(false)
const uploadRef = ref(null)
const uploadFile = ref(null)
const uploading = ref(false)
const uploadFormat = ref('xlsx')
const uploadPreview = ref('')

function onFileChange(file) {
  uploadFile.value = file.raw
  const ext = file.name.split('.').pop().toLowerCase()
  uploadFormat.value = ['csv', 'xlsx', 'xls'].includes(ext) ? 'xlsx' : 'jsonl'
  uploadPreview.value = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`
}

async function handleUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  const formData = new FormData()
  formData.append('file', uploadFile.value)

  uploading.value = true
  try {
    const result = await store.uploadSamples(datasetId, formData)
    showUploadDialog.value = false
    uploadFile.value = null
    uploadPreview.value = ''
    const uploaded = result.uploaded || result.count || 0
    const skipped = result.skipped || 0
    const errMsgs = (result.errors || []).slice(0, 3)
    let msg = `成功上传 ${uploaded} 个样本`
    if (skipped > 0) msg += `，跳过 ${skipped} 个`
    ElMessage.success(msg)
    if (errMsgs.length > 0) {
      console.warn('Upload errors:', errMsgs)
    }
    await loadSamples()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.response?.data?.error || e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// Version
const showVersionDialog = ref(false)
const newVersion = ref('')
const copySamples = ref(true)

async function handleCreateVersion() {
  if (!newVersion.value.trim()) {
    ElMessage.warning('请输入版本号')
    return
  }
  try {
    await store.createVersion(datasetId, { version: newVersion.value, copy_samples: copySamples.value })
    showVersionDialog.value = false
    ElMessage.success('新版本创建成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '创建版本失败')
  }
}

// Delete Sample
const showDeleteSampleDialog = ref(false)
const deleteSampleTarget = ref(null)

function confirmDeleteSample(sample) {
  deleteSampleTarget.value = sample
  showDeleteSampleDialog.value = true
}

async function handleDeleteSample() {
  if (!deleteSampleTarget.value) return
  try {
    await store.deleteSample(datasetId, deleteSampleTarget.value.id)
    showDeleteSampleDialog.value = false
    deleteSampleTarget.value = null
    ElMessage.success('样本已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '删除样本失败')
  }
}

// Edit Sample
const showEditDialog = ref(false)
const editSaving = ref(false)
const editForm = reactive({
  id: '',
  sample_id: '',
  input: '',
  expected_output: '',
  expected_meta: '',
  context: '',
  tags_raw: '',
  notes: '',
})
const editInputError = ref('')
const editOutputError = ref('')

function openEditDialog(sample) {
  editForm.id = sample.id
  editForm.sample_id = sample.sample_id || ''
  // Format JSON nicely for editing
  try {
    const inputObj = typeof sample.input === 'string' ? JSON.parse(sample.input) : sample.input
    editForm.input = JSON.stringify(inputObj, null, 2)
  } catch {
    editForm.input = sample.input || ''
  }
  try {
    const outputObj = typeof sample.expected_output === 'string' ? JSON.parse(sample.expected_output) : sample.expected_output
    editForm.expected_output = JSON.stringify(outputObj, null, 2)
  } catch {
    editForm.expected_output = sample.expected_output || ''
  }
  try {
    const ctxObj = typeof sample.context === 'string' ? JSON.parse(sample.context) : sample.context
    editForm.context = ctxObj && Array.isArray(ctxObj) && ctxObj.length ? JSON.stringify(ctxObj, null, 2) : ''
  } catch {
    editForm.context = ''
  }
  editForm.tags_raw = (sample.tags || []).join(', ')
  editForm.notes = sample.notes || ''
  // Format expected_meta
  try {
    const metaObj = typeof sample.expected_meta === 'string' ? JSON.parse(sample.expected_meta) : sample.expected_meta
    editForm.expected_meta = metaObj && Object.keys(metaObj).length ? JSON.stringify(metaObj, null, 2) : ''
  } catch {
    editForm.expected_meta = ''
  }
  editInputError.value = ''
  editOutputError.value = ''
  showEditDialog.value = true
}

async function handleSaveSample() {
  editInputError.value = ''
  editOutputError.value = ''

  let input, expectedOutput
  try {
    input = editForm.input.trim() ? JSON.parse(editForm.input) : {}
  } catch { editInputError.value = '输入 JSON 格式无效'; return }
  // expected_output: try JSON parse, fallback to plain text
  if (editForm.expected_output.trim()) {
    try {
      expectedOutput = JSON.parse(editForm.expected_output)
    } catch {
      expectedOutput = editForm.expected_output.trim()
    }
  } else {
    expectedOutput = ''
  }

  let context = []
  if (editForm.context.trim()) {
    try { context = JSON.parse(editForm.context) } catch { context = [editForm.context] }
  }

  const tags = editForm.tags_raw
    ? editForm.tags_raw.split(',').map(t => t.trim()).filter(Boolean)
    : []

  const payload = {
    input,
    expected_output: expectedOutput,
    context,
    tags,
    notes: editForm.notes,
  }
  // Parse expected_meta
  if (editForm.expected_meta.trim()) {
    try {
      payload.expected_meta = JSON.parse(editForm.expected_meta)
    } catch {
      ElMessage.error('期望 Meta JSON 格式无效')
      return
    }
  } else {
    payload.expected_meta = {}
  }

  editSaving.value = true
  try {
    await store.updateSample(datasetId, editForm.id, payload)
    showEditDialog.value = false
    ElMessage.success('样本已更新')
    await loadSamples()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '更新样本失败')
  } finally {
    editSaving.value = false
  }
}

onMounted(async () => {
  await loadDataset()
  if (dataset.value) {
    await loadSamples()
    // Handle sample_id query param: open edit dialog for target sample
    const targetSampleId = route.query.sample_id
    if (targetSampleId) {
      await openEditForSampleId(targetSampleId)
    }
  }
})

async function openEditForSampleId(sampleId) {
  // Load all samples to find the target
  try {
    const res = await store.fetchSamples(datasetId, { page: 1, page_size: 10000 })
    const samplesList = res.results || res || []
    const target = samplesList.find(s => s.sample_id === sampleId)
    if (target) {
      openEditDialog(target)
      // Clear the query param from URL to avoid re-triggering on refresh
      router.replace({ path: `/datasets/${datasetId}`, query: {} })
    }
  } catch {
    // Silently fail - sample may not exist or loading error
  }
}
</script>

<style scoped>
.dataset-detail-page { display: flex; flex-direction: column; gap: 16px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions { display: flex; gap: 8px; }

.loading-wrap { padding: 20px; }

.info-card {
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--info-card-gradient-end) 100%);
}
.info-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.ds-name { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }
.ds-desc { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.accent { color: #6C5CE7; font-weight: 600; }

.tag-list { display: flex; gap: 4px; flex-wrap: wrap; }
.ds-tag { background: rgba(108, 92, 231, 0.1) !important; border-color: rgba(108, 92, 231, 0.3) !important; color: #6C5CE7 !important; }

.samples-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
}
.sample-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(108, 92, 231, 0.15);
  color: #6C5CE7;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
}

.sample-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
}
.sample-id { font-family: monospace; font-size: 12px; color: #6C5CE7; }
.cell-text { font-size: 12px; color: var(--text-primary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.cell-text.muted { color: var(--text-secondary); }
.text-muted { color: var(--text-secondary); font-size: 12px; }

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  border-top: 1px solid var(--border-color);
}

.upload-area { text-align: center; }
.upload-hint { color: var(--text-secondary); font-size: 13px; margin-bottom: 16px; }
.upload-hint code { color: #6C5CE7; background: rgba(108, 92, 231, 0.1); padding: 1px 5px; border-radius: 3px; font-size: 12px; }

.upload-tabs {
  text-align: left;
  margin-bottom: 16px;
  --el-tabs-header-height: 36px;
}
.upload-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  color: var(--text-secondary);
}
.upload-tabs :deep(.el-tabs__item.is-active) {
  color: #6C5CE7;
}
.upload-tabs :deep(.el-tabs__active-bar) {
  background-color: #6C5CE7;
}
.format-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.8;
  padding: 8px 0;
}
.format-desc code {
  color: #6C5CE7;
  background: rgba(108, 92, 231, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
}
.format-desc ul {
  margin: 6px 0 0;
  padding-left: 18px;
}
.format-desc strong {
  color: var(--text-primary);
}
.upload-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
  padding: 8px;
  background: rgba(108, 92, 231, 0.08);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
}
</style>
