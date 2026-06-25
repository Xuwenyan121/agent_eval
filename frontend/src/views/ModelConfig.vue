<template>
  <div class="model-config-page">
    <h2 class="page-title">裁判模型配置</h2>
    <p class="page-desc">管理 LLM 裁判模型端点配置，用于评测任务的 G-Eval 等 LLM 裁判指标。</p>

    <div class="config-layout">
      <!-- Left: Model List -->
      <div class="model-sidebar">
        <div class="sidebar-toolbar">
          <el-input v-model="searchQuery" placeholder="搜索模型..." clearable size="small" @input="filterModels" />
          <el-button type="primary" size="small" @click="handleCreate">
            <el-icon><Plus /></el-icon> 新建
          </el-button>
        </div>
        <div class="sidebar-filters">
          <el-select v-model="filterProvider" placeholder="厂商" clearable size="small" @change="filterModels">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Azure OpenAI" value="azure" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="通义千问" value="qwen" />
            <el-option label="智谱 AI" value="zhipu" />
            <el-option label="Moonshot" value="moonshot" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </div>
        <div class="model-list" v-loading="modelStore.loading">
          <div
            v-for="m in filteredModels"
            :key="m.id"
            class="model-card"
            :class="{ active: currentId === m.id }"
            @click="selectModel(m.id)"
          >
            <div class="card-header">
              <span class="card-name">{{ m.display_name }}</span>
              <el-tag v-if="m.is_default" size="small" type="warning" effect="dark">默认</el-tag>
            </div>
            <div class="card-model">{{ m.model }}</div>
            <div class="card-meta">
              <el-tag size="small" :type="providerTag(m.provider)" effect="plain">{{ providerLabel(m.provider) }}</el-tag>
              <span v-if="m.masked_api_key" class="card-key">{{ m.masked_api_key }}</span>
              <span v-else class="card-no-key">无 Key</span>
            </div>
          </div>
          <div v-if="!modelStore.loading && filteredModels.length === 0" class="empty-list">
            暂无模型配置，点击"新建"添加
          </div>
        </div>
      </div>

      <!-- Right: Editor -->
      <div class="model-editor" v-if="currentId">
        <div class="editor-toolbar">
          <h3 class="editor-title">{{ isEditing ? (form.id ? '编辑模型' : '新建模型') : '模型详情' }}</h3>
          <div class="editor-actions">
            <template v-if="!isEditing">
              <el-button size="small" @click="isEditing = true">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
              <el-button size="small" @click="handleTest">
                <el-icon><Connection /></el-icon> 测试连接
              </el-button>
              <el-dropdown trigger="click" @command="handleCommand">
                <el-button size="small">
                  更多 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="setDefault" :disabled="modelStore.current?.is_default">
                      设为默认
                    </el-dropdown-item>
                    <el-dropdown-item command="duplicate">复制</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <span style="color: #FF3D71">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            <template v-else>
              <el-button size="small" @click="handleCancelEdit">取消</el-button>
              <el-button type="primary" size="small" :loading="modelStore.loading" @click="handleSave">
                保存
              </el-button>
            </template>
          </div>
        </div>

        <!-- View Mode -->
        <div v-if="!isEditing" class="detail-view">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">名称</span>
              <span class="detail-value">{{ modelStore.current?.display_name }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">标识</span>
              <span class="detail-value mono">{{ modelStore.current?.name }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">模型</span>
              <span class="detail-value accent">{{ modelStore.current?.model }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">厂商</span>
              <el-tag size="small" :type="providerTag(modelStore.current?.provider)" effect="plain">
                {{ providerLabel(modelStore.current?.provider) }}
              </el-tag>
            </div>
            <div class="detail-item full-width">
              <span class="detail-label">API Base</span>
              <span class="detail-value mono">{{ modelStore.current?.api_base || '(使用 OpenAI 默认)' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">API Key</span>
              <span class="detail-value mono">{{ modelStore.current?.masked_api_key || '未配置' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态</span>
              <el-tag :type="modelStore.current?.is_active ? 'success' : 'danger'" size="small">
                {{ modelStore.current?.is_active ? '启用' : '停用' }}
              </el-tag>
              <el-tag v-if="modelStore.current?.is_default" type="warning" size="small" style="margin-left: 6px">默认</el-tag>
            </div>
            <div class="detail-item full-width" v-if="modelStore.current?.description">
              <span class="detail-label">描述</span>
              <span class="detail-value">{{ modelStore.current?.description }}</span>
            </div>
            <div class="detail-item full-width" v-if="modelStore.current?.extra_params && Object.keys(modelStore.current.extra_params).length">
              <span class="detail-label">额外参数</span>
              <pre class="json-block">{{ JSON.stringify(modelStore.current.extra_params, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <!-- Edit Mode -->
        <div v-else class="edit-form">
          <el-form :model="form" label-position="top" class="model-form">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="显示名称" required>
                  <el-input v-model="form.display_name" placeholder="GPT-4o Production" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="标识名称" required>
                  <el-input v-model="form.name" placeholder="gpt4o_prod" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="模型" required>
                  <el-input v-model="form.model" placeholder="gpt-4o" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="厂商">
                  <el-select v-model="form.provider" style="width: 100%">
                    <el-option label="OpenAI" value="openai" />
                    <el-option label="Azure OpenAI" value="azure" />
                    <el-option label="DeepSeek" value="deepseek" />
                    <el-option label="通义千问" value="qwen" />
                    <el-option label="智谱 AI" value="zhipu" />
                    <el-option label="Moonshot" value="moonshot" />
                    <el-option label="自定义" value="custom" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="API Base URL">
              <el-input v-model="form.api_base" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="form.api_key" placeholder="sk-..." type="password" show-password />
              <span class="form-hint" v-if="form.id">留空则保持原有 Key 不变</span>
            </el-form-item>
            <el-form-item label="额外参数（JSON）">
              <el-input
                v-model="extraParamsStr"
                type="textarea"
                :rows="3"
                placeholder='{"temperature": 0.1, "max_tokens": 4096}'
              />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="备注说明..." />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="默认模型">
                  <el-switch v-model="form.is_default" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="启用">
                  <el-switch v-model="form.is_active" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>

        <!-- Test Results -->
        <div class="test-section" v-if="modelStore.testResult">
          <h4 class="section-title">连接测试结果</h4>
          <div class="test-result-box" :class="modelStore.testResult.success ? 'success' : 'error'">
            <div class="test-header">
              <el-icon :size="18">
                <component :is="modelStore.testResult.success ? 'CircleCheck' : 'CircleClose'" />
              </el-icon>
              <span>{{ modelStore.testResult.success ? '连接成功' : '连接失败' }}</span>
              <span class="test-latency">{{ modelStore.testResult.latency_ms }}ms</span>
            </div>
            <div class="test-body" v-if="modelStore.testResult.success">
              <p class="test-response">{{ modelStore.testResult.response }}</p>
              <p class="test-meta">模型: {{ modelStore.testResult.model }} · API: {{ modelStore.testResult.api_base }}</p>
            </div>
            <div class="test-body" v-else>
              <p class="test-error">{{ modelStore.testResult.error }}</p>
              <p class="test-meta" v-if="modelStore.testResult.status_code">HTTP {{ modelStore.testResult.status_code }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div class="model-editor empty-editor" v-else>
        <el-empty description="选择一个模型配置进行编辑，或新建一个" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useJudgeModelStore } from '@/stores/judgeModels'
import { ElMessage, ElMessageBox } from 'element-plus'

const modelStore = useJudgeModelStore()

const searchQuery = ref('')
const filterProvider = ref('')
const currentId = ref(null)
const isEditing = ref(false)
const extraParamsStr = ref('')

const form = ref(emptyForm())

function emptyForm() {
  return {
    id: null,
    name: '',
    display_name: '',
    description: '',
    model: '',
    api_base: '',
    api_key: '',
    extra_params: {},
    provider: 'custom',
    is_default: false,
    is_active: true,
  }
}

// Provider helpers
const providerMap = {
  openai: 'OpenAI', azure: 'Azure', deepseek: 'DeepSeek',
  qwen: '通义千问', zhipu: '智谱 AI', moonshot: 'Moonshot', custom: '自定义',
}
const providerLabel = (p) => providerMap[p] || p
const providerTag = (p) => ({
  openai: 'success', azure: 'primary', deepseek: 'warning',
  qwen: 'danger', zhipu: 'info', moonshot: '', custom: 'info',
})[p] || 'info'

// Filtered list
const filteredModels = computed(() => {
  let list = modelStore.models
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(m =>
      m.display_name.toLowerCase().includes(q) ||
      m.model.toLowerCase().includes(q) ||
      m.name.toLowerCase().includes(q)
    )
  }
  if (filterProvider.value) {
    list = list.filter(m => m.provider === filterProvider.value)
  }
  return list
})

function filterModels() { /* reactive via computed */ }

async function selectModel(id) {
  currentId.value = id
  isEditing.value = false
  modelStore.clearTestResult()
  await modelStore.fetchModel(id)
}

function handleCreate() {
  currentId.value = '__new__'
  isEditing.value = true
  form.value = emptyForm()
  extraParamsStr.value = ''
  modelStore.current = null
}

watch(currentId, (val) => {
  if (val === '__new__') return
  if (modelStore.current) {
    form.value = { ...modelStore.current, api_key: '' }
    extraParamsStr.value = modelStore.current.extra_params
      ? JSON.stringify(modelStore.current.extra_params, null, 2)
      : ''
  }
})

async function handleSave() {
  if (!form.value.display_name || !form.value.model) {
    ElMessage.warning('请填写显示名称和模型')
    return
  }

  // Parse extra params
  let extraParams = {}
  if (extraParamsStr.value.trim()) {
    try {
      extraParams = JSON.parse(extraParamsStr.value)
    } catch {
      ElMessage.error('额外参数 JSON 格式错误')
      return
    }
  }

  const data = {
    name: form.value.name || form.value.display_name.toLowerCase().replace(/\s+/g, '_'),
    display_name: form.value.display_name,
    description: form.value.description,
    model: form.value.model,
    api_base: form.value.api_base,
    api_key: form.value.api_key,
    extra_params: extraParams,
    provider: form.value.provider,
    is_default: form.value.is_default,
    is_active: form.value.is_active,
  }

  try {
    if (form.value.id && form.value.id !== '__new__') {
      await modelStore.updateModel(form.value.id, data)
      ElMessage.success('模型配置已更新')
    } else {
      const created = await modelStore.createModel(data)
      currentId.value = created.id
      ElMessage.success('模型配置已创建')
    }
    isEditing.value = false
    modelStore.clearTestResult()
  } catch (e) {
    const errors = e.response?.data
    if (typeof errors === 'object') {
      const msgs = Object.entries(errors).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
      ElMessage.error(msgs.join(' | '))
    } else {
      ElMessage.error('保存失败')
    }
  }
}

function handleCancelEdit() {
  if (currentId.value === '__new__') {
    currentId.value = null
  } else {
    isEditing.value = false
    // Reset form to current model data
    if (modelStore.current) {
      form.value = { ...modelStore.current, api_key: '' }
      extraParamsStr.value = modelStore.current.extra_params
        ? JSON.stringify(modelStore.current.extra_params, null, 2)
        : ''
    }
  }
}

async function handleTest() {
  const payload = {}
  if (currentId.value && currentId.value !== '__new__') {
    payload.model_id = currentId.value
  } else {
    payload.model = form.value.model
    payload.api_base = form.value.api_base
    payload.api_key = form.value.api_key
  }
  try {
    await modelStore.testModel(payload)
  } catch {
    // testResult is already set in the store
  }
}

async function handleCommand(cmd) {
  if (cmd === 'setDefault') {
    await modelStore.setDefault(currentId.value)
    ElMessage.success('已设为默认模型')
    await modelStore.fetchModel(currentId.value)
  } else if (cmd === 'duplicate') {
    const clone = await modelStore.duplicateModel(currentId.value)
    currentId.value = clone.id
    ElMessage.success('已复制模型配置')
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm('确定删除此模型配置？', '确认删除', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await modelStore.deleteModel(currentId.value)
      currentId.value = null
      ElMessage.success('已删除')
    } catch { /* cancelled */ }
  }
}

onMounted(() => {
  modelStore.fetchModels()
})
</script>

<style scoped>
.model-config-page { display: flex; flex-direction: column; gap: 12px; }
.page-title { font-size: 20px; font-weight: 600; color: #E8E8ED; margin: 0; }
.page-desc { color: #9498A6; font-size: 13px; margin: 0; }

.config-layout { display: flex; gap: 16px; min-height: calc(100vh - 180px); }

/* Sidebar */
.model-sidebar {
  width: 300px; min-width: 280px;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px;
  display: flex; flex-direction: column; overflow: hidden;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}
.sidebar-toolbar { display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid var(--border-color); }
.sidebar-filters { padding: 8px 12px; border-bottom: 1px solid var(--border-color); }
.sidebar-filters .el-select { width: 100%; }

.model-list { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px; }

.model-card {
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid transparent; transition: all 0.15s;
}
.model-card:hover { background: var(--bg-hover); border-color: var(--border-color); }
.model-card.active { background: var(--bg-active); border-color: var(--tag-border); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.card-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.card-model { font-size: 12px; color: var(--accent-start); font-family: monospace; margin-bottom: 4px; }
.card-meta { display: flex; align-items: center; gap: 6px; }
.card-key { font-size: 10px; color: var(--text-muted); font-family: monospace; letter-spacing: 1px; }
.card-no-key { font-size: 10px; color: var(--danger); }
.empty-list { text-align: center; color: var(--text-muted); font-size: 12px; padding: 40px 12px; }

/* Editor */
.model-editor {
  flex: 1; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px;
  padding: 20px; display: flex; flex-direction: column; gap: 16px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}
.empty-editor { align-items: center; justify-content: center; }
.editor-toolbar { display: flex; justify-content: space-between; align-items: center; }
.editor-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0; }
.editor-actions { display: flex; gap: 8px; }

/* Detail View */
.detail-grid { display: flex; flex-wrap: wrap; gap: 16px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; min-width: 180px; }
.detail-item.full-width { width: 100%; }
.detail-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.detail-value { font-size: 13px; color: var(--text-primary); }
.detail-value.accent { color: var(--accent-start); font-weight: 600; }
.detail-value.mono { font-family: monospace; font-size: 12px; }
.json-block { color: var(--text-primary); font-size: 12px; font-family: monospace; background: var(--code-bg); padding: 8px; border-radius: 6px; margin: 0; white-space: pre-wrap; }

/* Edit Form */
.model-form { display: flex; flex-direction: column; gap: 4px; }
.form-hint { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* Test Section */
.test-section { margin-top: 8px; border-top: 1px solid var(--border-color); padding-top: 16px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0 0 10px; }
.test-result-box {
  border-radius: 8px; padding: 14px;
  border: 1px solid var(--border-color);
}
.test-result-box.success { background: rgba(0, 214, 143, 0.06); border-color: rgba(0, 214, 143, 0.2); }
.test-result-box.error { background: rgba(255, 61, 113, 0.06); border-color: rgba(255, 61, 113, 0.2); }
.test-header { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 8px; }
.test-result-box.success .test-header .el-icon { color: var(--success); }
.test-result-box.error .test-header .el-icon { color: var(--danger); }
.test-latency { margin-left: auto; font-size: 12px; color: var(--text-muted); font-family: monospace; }
.test-response { color: var(--text-primary); font-size: 13px; margin: 0 0 6px; }
.test-error { color: var(--danger); font-size: 13px; margin: 0 0 6px; }
.test-meta { color: var(--text-muted); font-size: 11px; margin: 0; font-family: monospace; }
</style>
