<template>
  <div class="prompt-library">
    <h2 class="page-title">裁判 Prompt 设计</h2>

    <div class="library-layout">
      <!-- Left: Prompt List -->
      <div class="prompt-sidebar">
        <div class="sidebar-toolbar">
          <el-input v-model="searchQuery" placeholder="搜索 Prompt..." clearable size="small" @input="loadPrompts" />
          <el-button type="primary" size="small" @click="handleCreate">
            <el-icon><Plus /></el-icon> 新建
          </el-button>
        </div>
        <div class="sidebar-filters">
          <el-select v-model="filterCategory" placeholder="分类" clearable size="small" @change="loadPrompts">
            <el-option label="通用" value="general" />
            <el-option label="正确性" value="correctness" />
            <el-option label="相关性" value="relevance" />
            <el-option label="忠实度" value="faithfulness" />
            <el-option label="安全性" value="safety" />
            <el-option label="领域专用" value="domain_specific" />
          </el-select>
        </div>
        <div class="prompt-list" v-loading="store.loading">
          <div
            v-for="p in store.prompts"
            :key="p.id"
            class="prompt-card"
            :class="{ active: currentId === p.id }"
            @click="selectPrompt(p.id)"
          >
            <div class="card-header">
              <span class="card-name">{{ p.display_name }}</span>
              <el-tag size="small" :type="categoryTag(p.category)" effect="plain">
                {{ categoryLabel(p.category) }}
              </el-tag>
            </div>
            <div class="card-meta">
              <span class="card-id">{{ p.name }}</span>
              <span class="card-lang">{{ p.language === 'zh' ? '中文' : 'EN' }}</span>
              <span v-if="!p.is_active" class="card-inactive">已停用</span>
            </div>
          </div>
          <div v-if="!store.loading && store.prompts.length === 0" class="empty-list">
            暂无 Prompt，点击"新建"创建第一个
          </div>
        </div>
      </div>

      <!-- Right: Editor -->
      <div class="prompt-editor" v-if="form">
        <div class="editor-header">
          <h3>{{ isNew ? '新建 Prompt' : form.display_name }}</h3>
          <div class="editor-actions">
            <el-button size="small" @click="handleDuplicate" :disabled="isNew">复制</el-button>
            <el-button size="small" type="danger" @click="handleDelete" :disabled="isNew">删除</el-button>
            <el-button size="small" type="primary" @click="handleSave" :loading="saving">保存</el-button>
          </div>
        </div>

        <el-tabs v-model="editorTab" class="editor-tabs">
          <!-- Tab: Basic Info -->
          <el-tab-pane label="基本信息" name="basic">
            <el-form :model="form" label-width="100px" size="small">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="标识名">
                    <el-input v-model="form.name" placeholder="correctness_zh" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="显示名称">
                    <el-input v-model="form.display_name" placeholder="正确性评估" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="描述">
                <el-input v-model="form.description" type="textarea" :rows="2" placeholder="这个 Prompt 评估什么..." />
              </el-form-item>
              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="分类">
                    <el-select v-model="form.category" style="width: 100%">
                      <el-option label="通用" value="general" />
                      <el-option label="正确性" value="correctness" />
                      <el-option label="相关性" value="relevance" />
                      <el-option label="忠实度" value="faithfulness" />
                      <el-option label="安全性" value="safety" />
                      <el-option label="领域专用" value="domain_specific" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="语言">
                    <el-select v-model="form.language" style="width: 100%">
                      <el-option label="中文" value="zh" />
                      <el-option label="English" value="en" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="启用">
                    <el-switch v-model="form.is_active" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-tab-pane>

          <!-- Tab: Prompt Template -->
          <el-tab-pane label="Prompt 模板" name="template">
            <div class="template-section">
              <h4>System Prompt（可选）</h4>
              <el-input v-model="form.system_prompt" type="textarea" :rows="3" placeholder="你是一个专业的AI评估专家..." />
            </div>
            <div class="template-section">
              <h4>评估标准（Criteria）</h4>
              <el-input v-model="form.criteria" type="textarea" :rows="6" placeholder="评估智能体的回复是否..." />
            </div>
            <div class="template-section">
              <h4>评估步骤</h4>
              <p class="section-hint">按顺序定义评估的思考步骤（Chain-of-Thought）</p>
              <div v-for="(step, idx) in form.evaluation_steps" :key="idx" class="step-row">
                <span class="step-num">{{ idx + 1 }}.</span>
                <el-input v-model="form.evaluation_steps[idx]" size="small" :placeholder="`步骤 ${idx + 1}`" />
                <el-button text type="danger" size="small" @click="form.evaluation_steps.splice(idx, 1)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <el-button size="small" @click="form.evaluation_steps.push('')">
                <el-icon><Plus /></el-icon> 添加步骤
              </el-button>
            </div>
          </el-tab-pane>

          <!-- Tab: Scoring Rubric -->
          <el-tab-pane label="评分标准" name="rubric">
            <p class="section-hint">定义每个分数等级对应的描述</p>
            <div class="rubric-table">
              <div v-for="score in rubricScores" :key="score" class="rubric-row">
                <div class="rubric-score">{{ score }} 分</div>
                <el-input
                  v-model="form.scoring_rubric[score]"
                  size="small"
                  :placeholder="`${score}分的描述...`"
                />
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab: Few-shot Examples -->
          <el-tab-pane label="示例" name="examples">
            <p class="section-hint">提供评估示例帮助 LLM 理解评分标准</p>
            <div v-for="(ex, idx) in form.few_shot_examples" :key="idx" class="example-card">
              <div class="example-header">
                <span>示例 {{ idx + 1 }}</span>
                <el-button text type="danger" size="small" @click="form.few_shot_examples.splice(idx, 1)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <el-row :gutter="8">
                <el-col :span="24">
                  <el-input v-model="ex.input" size="small" placeholder="用户输入" />
                </el-col>
              </el-row>
              <el-row :gutter="8">
                <el-col :span="12">
                  <el-input v-model="ex.actual_output" size="small" type="textarea" :rows="2" placeholder="智能体回复" />
                </el-col>
                <el-col :span="12">
                  <el-input v-model="ex.expected_output" size="small" type="textarea" :rows="2" placeholder="期望答案" />
                </el-col>
              </el-row>
              <el-row :gutter="8">
                <el-col :span="6">
                  <el-input-number v-model="ex.score" :min="1" :max="5" size="small" controls-position="right" style="width: 100%" />
                </el-col>
                <el-col :span="18">
                  <el-input v-model="ex.reason" size="small" placeholder="评分理由" />
                </el-col>
              </el-row>
            </div>
            <el-button size="small" @click="form.few_shot_examples.push({ input: '', actual_output: '', expected_output: '', score: 3, reason: '' })">
              <el-icon><Plus /></el-icon> 添加示例
            </el-button>
          </el-tab-pane>

          <!-- Tab: Preview -->
          <el-tab-pane label="预览" name="preview">
            <div class="preview-section">
              <el-button size="small" @click="handlePreview" :loading="previewLoading">
                渲染 Prompt
              </el-button>
              <div v-if="previewData" class="preview-result">
                <div class="preview-block">
                  <h5>System Prompt</h5>
                  <pre class="preview-text">{{ previewData.system_prompt || '(未设置)' }}</pre>
                </div>
                <div class="preview-block">
                  <h5>完整评估标准</h5>
                  <pre class="preview-text">{{ previewData.assembled_criteria }}</pre>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab: Dry Run -->
          <el-tab-pane label="调试测试" name="dryrun">
            <div class="dryrun-section">
              <h4>样本数据</h4>
              <el-row :gutter="8">
                <el-col :span="24">
                  <el-input v-model="dryRunSample.input" type="textarea" :rows="2" placeholder="用户输入" />
                </el-col>
              </el-row>
              <el-row :gutter="8" style="margin-top: 8px">
                <el-col :span="12">
                  <el-input v-model="dryRunSample.actual_output" type="textarea" :rows="3" placeholder="智能体回复" />
                </el-col>
                <el-col :span="12">
                  <el-input v-model="dryRunSample.expected_output" type="textarea" :rows="3" placeholder="期望答案" />
                </el-col>
              </el-row>
              <h4 style="margin-top: 12px">裁判模型</h4>
              <el-select
                v-model="dryRunModelId"
                placeholder="选择预设模型（或手动填写）"
                clearable
                filterable
                style="width: 100%; margin-bottom: 8px"
                @change="onDryRunModelSelect"
              >
                <el-option
                  v-for="m in judgeModelStore.activeModels"
                  :key="m.id"
                  :label="`${m.display_name} — ${m.model}`"
                  :value="m.id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ m.display_name }}</span>
                    <el-tag v-if="m.is_default" size="small" type="warning" effect="dark">默认</el-tag>
                  </div>
                </el-option>
              </el-select>
              <el-row :gutter="8">
                <el-col :span="8">
                  <el-input v-model="dryRunJudge.model" placeholder="gpt-4o" />
                </el-col>
                <el-col :span="8">
                  <el-input v-model="dryRunJudge.api_base" placeholder="API Base (可选)" />
                </el-col>
                <el-col :span="8">
                  <el-input v-model="dryRunJudge.api_key" placeholder="API Key" type="password" show-password />
                </el-col>
              </el-row>
              <el-button type="primary" size="small" style="margin-top: 12px" @click="handleDryRun" :loading="store.dryRunLoading">
                运行测试
              </el-button>

              <div v-if="store.dryRunResult" class="dryrun-result">
                <div class="result-header">
                  <span class="result-score" :class="scoreClass(store.dryRunResult.score)">
                    {{ (store.dryRunResult.score * 100).toFixed(1) }}%
                  </span>
                  <span class="result-latency">{{ store.dryRunResult.latency_ms }}ms</span>
                </div>
                <div class="result-reason">{{ store.dryRunResult.reason || '(无详细理由)' }}</div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Empty state -->
      <div class="prompt-editor" v-else>
        <div class="empty-editor">
          <p>选择左侧的 Prompt 进行编辑，或点击"新建"创建</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePromptStore } from '@/stores/prompts'
import { useJudgeModelStore } from '@/stores/judgeModels'

const store = usePromptStore()
const judgeModelStore = useJudgeModelStore()

const searchQuery = ref('')
const filterCategory = ref('')
const currentId = ref(null)
const isNew = ref(false)
const saving = ref(false)
const editorTab = ref('basic')
const previewLoading = ref(false)
const previewData = ref(null)

const form = ref(null)
const rubricScores = ['1', '2', '3', '4', '5']

const dryRunSample = reactive({ input: '', actual_output: '', expected_output: '' })
const dryRunJudge = reactive({ model: '', api_base: '', api_key: '' })
const dryRunModelId = ref(null)

function onDryRunModelSelect(id) {
  if (!id) {
    dryRunJudge.model = ''
    dryRunJudge.api_base = ''
    dryRunJudge.api_key = ''
    return
  }
  const preset = judgeModelStore.models.find(m => m.id === id)
  if (preset) {
    dryRunJudge.model = preset.model
    dryRunJudge.api_base = preset.api_base || ''
    dryRunJudge.api_key = ''
  }
}

// Labels
const categoryLabels = { general: '通用', correctness: '正确性', relevance: '相关性', faithfulness: '忠实度', safety: '安全性', domain_specific: '领域专用' }
const categoryLabel = (c) => categoryLabels[c] || c
const categoryTag = (c) => ({ general: '', correctness: 'success', relevance: 'primary', faithfulness: 'warning', safety: 'danger', domain_specific: 'info' })[c] || 'info'

const scoreClass = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
}

function emptyForm() {
  return {
    name: '', display_name: '', description: '',
    system_prompt: '', criteria: '', evaluation_steps: [],
    scoring_rubric: { '1': '', '2': '', '3': '', '4': '', '5': '' },
    few_shot_examples: [],
    variables: ['input', 'actual_output', 'expected_output'],
    category: 'general', language: 'zh', version: 1, is_active: true,
  }
}

async function loadPrompts() {
  const params = {}
  if (filterCategory.value) params.category = filterCategory.value
  if (searchQuery.value) params.search = searchQuery.value
  await store.fetchPrompts(params)
}

async function selectPrompt(id) {
  currentId.value = id
  isNew.value = false
  previewData.value = null
  editorTab.value = 'basic'
  try {
    const prompt = await store.fetchPrompt(id)
    // Ensure all fields exist
    form.value = {
      ...emptyForm(),
      ...prompt,
      scoring_rubric: prompt.scoring_rubric && Object.keys(prompt.scoring_rubric).length > 0
        ? { ...prompt.scoring_rubric }
        : { '1': '', '2': '', '3': '', '4': '', '5': '' },
      evaluation_steps: [...(prompt.evaluation_steps || [])],
      few_shot_examples: [...(prompt.few_shot_examples || [])],
    }
  } catch (e) {
    ElMessage.error('加载 Prompt 失败')
  }
}

function handleCreate() {
  currentId.value = null
  isNew.value = true
  form.value = emptyForm()
  editorTab.value = 'basic'
  previewData.value = null
}

async function handleSave() {
  if (!form.value.name || !form.value.display_name || !form.value.criteria) {
    ElMessage.warning('请填写标识名、显示名称和评估标准')
    return
  }
  saving.value = true
  try {
    if (isNew.value) {
      const created = await store.createPrompt(form.value)
      currentId.value = created.id
      isNew.value = false
      ElMessage.success('创建成功')
    } else {
      await store.updatePrompt(currentId.value, form.value)
      ElMessage.success('保存成功')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.name?.[0] || e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDuplicate() {
  try {
    const clone = await store.duplicatePrompt(currentId.value)
    ElMessage.success('复制成功')
    await selectPrompt(clone.id)
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确认删除此 Prompt？', '删除确认', { type: 'warning' })
    await store.deletePrompt(currentId.value)
    currentId.value = null
    form.value = null
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handlePreview() {
  if (!currentId.value || isNew.value) {
    ElMessage.warning('请先保存 Prompt 再预览')
    return
  }
  previewLoading.value = true
  try {
    previewData.value = await store.previewPrompt(currentId.value, {})
  } catch (e) {
    ElMessage.error('预览失败')
  } finally {
    previewLoading.value = false
  }
}

async function handleDryRun() {
  if (!dryRunSample.input && !dryRunSample.actual_output) {
    ElMessage.warning('请输入样本数据')
    return
  }
  if (!dryRunJudge.model) {
    ElMessage.warning('请配置裁判模型')
    return
  }
  const payload = {
    prompt_id: isNew.value ? null : currentId.value,
    criteria: form.value.criteria,
    evaluation_steps: form.value.evaluation_steps.filter(s => s),
    sample: { ...dryRunSample },
    judge_model: { model: dryRunJudge.model },
  }
  if (dryRunJudge.api_base) payload.judge_model.api_base = dryRunJudge.api_base
  if (dryRunJudge.api_key) payload.judge_model.api_key = dryRunJudge.api_key

  try {
    await store.dryRun(payload)
    ElMessage.success('测试完成')
  } catch (e) {
    const msg = e.response?.data?.error || e.message
    ElMessage.error(msg || '测试失败')
  }
}

onMounted(() => {
  loadPrompts()
  judgeModelStore.fetchModels({ is_active: 'true' }).then(() => {
    const def = judgeModelStore.defaultModel
    if (def) {
      dryRunModelId.value = def.id
      onDryRunModelSelect(def.id)
    }
  })
})
</script>

<style scoped>
.prompt-library { display: flex; flex-direction: column; gap: 12px; }
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0; }

.library-layout { display: flex; gap: 16px; min-height: 600px; }

/* Sidebar */
.prompt-sidebar {
  width: 280px; min-width: 280px;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px;
  display: flex; flex-direction: column; padding: 12px;
}
.sidebar-toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
.sidebar-filters { margin-bottom: 8px; }
.sidebar-filters .el-select { width: 100%; }

.prompt-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.prompt-card {
  padding: 10px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border-color); transition: all 0.15s;
}
.prompt-card:hover { border-color: var(--accent-start); }
.prompt-card.active { border-color: var(--accent-start); background: rgba(108, 92, 231, 0.1); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.card-name { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.card-meta { display: flex; gap: 8px; font-size: 11px; color: var(--text-muted); }
.card-id { font-family: monospace; }
.card-lang { color: var(--text-secondary); }
.card-inactive { color: var(--danger); }
.empty-list { text-align: center; color: var(--text-muted); font-size: 12px; padding: 40px 0; }

/* Editor */
.prompt-editor {
  flex: 1; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px;
  padding: 16px; overflow-y: auto;
}
.editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.editor-header h3 { color: var(--text-primary); font-size: 16px; margin: 0; }
.editor-actions { display: flex; gap: 8px; }

.empty-editor { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); }

.editor-tabs :deep(.el-tabs__item) { color: var(--text-secondary); font-size: 13px; }
.editor-tabs :deep(.el-tabs__item.is-active) { color: var(--accent-start); }
.editor-tabs :deep(.el-tabs__active-bar) { background: var(--accent-start); }
.editor-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-color); }

/* Template section */
.template-section { margin-bottom: 16px; }
.template-section h4 { color: var(--text-primary); font-size: 13px; margin: 0 0 6px; }
.section-hint { color: var(--text-muted); font-size: 11px; margin: 0 0 8px; }
.step-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.step-num { color: var(--text-secondary); font-size: 12px; min-width: 20px; }

/* Rubric */
.rubric-table { display: flex; flex-direction: column; gap: 8px; }
.rubric-row { display: flex; gap: 12px; align-items: center; }
.rubric-score { color: var(--text-primary); font-size: 13px; font-weight: 500; min-width: 50px; }

/* Examples */
.example-card {
  background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px;
  padding: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px;
}
.example-header { display: flex; justify-content: space-between; align-items: center; }
.example-header span { color: var(--text-secondary); font-size: 12px; font-weight: 500; }

/* Preview */
.preview-section { display: flex; flex-direction: column; gap: 12px; }
.preview-block { margin-bottom: 12px; }
.preview-block h5 { color: var(--text-secondary); font-size: 12px; margin: 0 0 4px; }
.preview-text {
  background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px;
  padding: 12px; color: var(--text-primary); font-size: 12px; white-space: pre-wrap;
  line-height: 1.6; margin: 0;
}

/* Dry Run */
.dryrun-section h4 { color: var(--text-primary); font-size: 13px; margin: 0 0 8px; }
.dryrun-result {
  margin-top: 16px; background: var(--bg-input); border: 1px solid var(--border-color);
  border-radius: 8px; padding: 14px;
}
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.result-score { font-size: 20px; font-weight: 700; }
.result-score.success { color: var(--success); }
.result-score.warning { color: var(--warning); }
.result-score.danger { color: var(--danger); }
.result-latency { color: var(--text-muted); font-size: 12px; }
.result-reason { color: var(--text-primary); font-size: 12px; line-height: 1.6; }
</style>
