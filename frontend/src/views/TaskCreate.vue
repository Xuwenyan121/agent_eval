<template>
  <div class="task-create-page">
    <!-- Header -->
    <div class="page-header">
      <el-button text @click="$router.push('/tasks')" class="back-btn">
        <el-icon><ArrowLeft /></el-icon>
        返回任务列表
      </el-button>
    </div>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="create-form">
      <!-- Section 1: Basic Info -->
      <div class="card section">
        <h4 class="section-title">基本信息</h4>
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：问答准确率测试 - v1" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="智能体" prop="agent">
              <el-select
                v-model="form.agent"
                placeholder="选择智能体"
                style="width: 100%"
                filterable
                :loading="agentsLoading"
              >
                <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id">
                  <div class="option-row">
                    <span>{{ a.name }}</span>
                    <el-tag size="small" effect="plain" style="margin-left: auto">{{ a.protocol }}</el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据集" prop="dataset">
              <el-select
                v-model="form.dataset"
                placeholder="选择数据集"
                style="width: 100%"
                filterable
                :loading="datasetsLoading"
              >
                <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id">
                  <div class="option-row">
                    <span>{{ d.name }}</span>
                    <span class="option-meta">{{ d.sample_count }} 样本 · {{ d.version }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Section 2: Judge Model -->
      <div class="card section">
        <h4 class="section-title">裁判模型</h4>
        <p class="section-desc">用于评估智能体回复的 LLM 裁判（规则类指标可选）。可从模型库选择预设或手动配置。</p>
        <el-form-item label="选择预设模型">
          <el-select
            v-model="selectedJudgeModelId"
            placeholder="从模型库选择（或手动填写下方）"
            clearable
            filterable
            style="width: 100%"
            @change="onJudgeModelSelect"
          >
            <el-option
              v-for="m in judgeModelStore.activeModels"
              :key="m.id"
              :label="`${m.display_name} — ${m.model}`"
              :value="m.id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>{{ m.display_name }}</span>
                <span style="display: flex; gap: 6px; align-items: center">
                  <el-tag v-if="m.is_default" size="small" type="warning" effect="dark">默认</el-tag>
                  <el-tag size="small" effect="plain" type="info">{{ m.model }}</el-tag>
                </span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-divider content-position="left" style="margin: 12px 0">或手动配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="模型">
              <el-input v-model="judge.model" placeholder="gpt-4o" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="API 基础地址">
              <el-input v-model="judge.api_base" placeholder="https://api.openai.com/v1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="API Key">
              <el-input v-model="judge.api_key" placeholder="sk-..." type="password" show-password />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Section 3: Evaluator Config -->
      <div class="card section">
        <h4 class="section-title">评测指标</h4>
        <p class="section-desc">配置指标及其权重，权重总和应为 1.0。</p>

        <div class="metrics-list">
          <div v-for="(metric, idx) in metrics" :key="idx" class="metric-row">
            <el-row :gutter="12" align="middle">
              <el-col :span="6">
                <el-select v-model="metric.type" placeholder="指标类型" style="width: 100%" @change="onMetricTypeChange(idx)">
                  <el-option-group label="规则类">
                    <el-option label="精确匹配" value="exact_match" />
                    <el-option label="包含" value="contains" />
                    <el-option label="正则匹配" value="regex_match" />
                    <el-option label="JSON 合法性" value="json_valid" />
                    <el-option label="长度检查" value="length_check" />
                    <el-option label="F1 分数" value="f1" />
                    <el-option label="ROUGE-L" value="rouge_l" />
                    <el-option label="BLEU 分数" value="bleu" />
                    <el-option label="字符串相似度" value="string_similarity" />
                    <el-option label="长度比" value="length_ratio" />
                    <el-option label="关键词覆盖率" value="keyword_coverage" />
                    <el-option label="元数据验证" value="meta_validation" />
                  </el-option-group>
                  <el-option-group label="LLM 裁判">
                    <el-option label="正确性" value="correctness" />
                    <el-option label="相关性" value="relevance" />
                    <el-option label="忠实度" value="faithfulness" />
                    <el-option label="幻觉检测" value="hallucination" />
                    <el-option label="回答质量" value="answer_quality" />
                  </el-option-group>
                </el-select>
              </el-col>
              <el-col :span="5" v-if="isLlmJudgeMetric(metric.type)">
                <el-select v-model="metric.prompt_id" placeholder="选择 Prompt" clearable style="width: 100%" size="small">
                  <el-option
                    v-for="p in promptStore.prompts"
                    :key="p.id"
                    :label="p.display_name"
                    :value="p.id"
                  />
                </el-select>
              </el-col>
              <el-col :span="isLlmJudgeMetric(metric.type) ? 3 : 4">
                <el-input-number v-model="metric.weight" :min="0" :max="1" :step="0.1" :precision="1" size="small" controls-position="right" style="width: 100%" />
              </el-col>
              <el-col :span="isLlmJudgeMetric(metric.type) ? 7 : 8">
                <el-input v-model="metric.threshold" placeholder="阈值（如 0.8）" size="small" />
              </el-col>
              <el-col :span="3">
                <el-button text type="danger" @click="removeMetric(idx)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </el-col>
            </el-row>
          </div>
        </div>

        <div class="metrics-footer">
          <el-button size="small" @click="addMetric">
            <el-icon><Plus /></el-icon>
            添加指标
          </el-button>
          <span class="weight-sum" :class="{ valid: isWeightValid }">
            权重总和：{{ weightSum.toFixed(1) }} / 1.0
          </span>
        </div>
      </div>

      <!-- Section 4: Execution Settings -->
      <div class="card section">
        <h4 class="section-title">执行设置</h4>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="并发请求数">
              <el-input-number v-model="form.parallel" :min="1" :max="50" style="width: 100%" />
              <span class="field-hint">最大并发智能体调用数</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="样本限制">
              <el-input-number v-model="form.limit" :min="0" :max="10000" :step="10" style="width: 100%" placeholder="0 = 全部" />
              <span class="field-hint">0 或留空 = 使用全部样本</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="会话 ID 策略">
              <el-select v-model="form.conv_id_strategy" style="width: 100%">
                <el-option label="数据集驱动（多轮会话）" value="dataset">
                  <div class="option-row">
                    <span>数据集驱动</span>
                    <el-tag size="small" effect="plain" style="margin-left: auto">多轮</el-tag>
                  </div>
                </el-option>
                <el-option label="独立会话（单轮）" value="isolated">
                  <div class="option-row">
                    <span>独立会话</span>
                    <el-tag size="small" effect="plain" style="margin-left: auto">单轮</el-tag>
                  </div>
                </el-option>
                <el-option label="共享会话（同一 convId）" value="shared">
                  <div class="option-row">
                    <span>共享会话</span>
                    <el-tag size="small" effect="plain" style="margin-left: auto">同一会话</el-tag>
                  </div>
                </el-option>
              </el-select>
              <span class="field-hint">控制 convId 分配方式</span>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <el-button @click="$router.push('/tasks')">取消</el-button>
        <el-button class="btn-gradient" :loading="store.loading" @click="handleSubmit">
          创建任务
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'
import { useAgentStore } from '@/stores/agents'
import { useDatasetStore } from '@/stores/datasets'
import { usePromptStore } from '@/stores/prompts'
import { useJudgeModelStore } from '@/stores/judgeModels'
import { agentApi, datasetApi } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const store = useTaskStore()
const agentStore = useAgentStore()
const datasetStore = useDatasetStore()
const promptStore = usePromptStore()
const judgeModelStore = useJudgeModelStore()

const formRef = ref(null)
const agents = ref([])
const datasets = ref([])
const agentsLoading = ref(false)
const datasetsLoading = ref(false)

const form = reactive({
  name: '',
  agent: null,
  dataset: null,
  parallel: 10,
  limit: 0,
  conv_id_strategy: 'dataset',
})

const judge = reactive({
  model: '',
  api_base: '',
  api_key: '',
})

const selectedJudgeModelId = ref(null)

function onJudgeModelSelect(id) {
  if (!id) {
    judge.model = ''
    judge.api_base = ''
    judge.api_key = ''
    return
  }
  const preset = judgeModelStore.models.find(m => m.id === id)
  if (preset) {
    judge.model = preset.model
    judge.api_base = preset.api_base || ''
    judge.api_key = preset.masked_api_key ? '' : '' // Don't expose masked key
    // If the preset has an API key set, we'll use the preset's id to resolve it server-side
  }
}

const metrics = ref([
  { type: 'exact_match', weight: 0.5, threshold: '', prompt_id: null },
  { type: 'correctness', weight: 0.5, threshold: '0.8', prompt_id: null },
])

const llmJudgeTypes = ['correctness', 'relevance', 'faithfulness', 'hallucination', 'answer_quality']
const isLlmJudgeMetric = (type) => llmJudgeTypes.includes(type)

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  agent: [{ required: true, message: '请选择智能体', trigger: 'change' }],
  dataset: [{ required: true, message: '请选择数据集', trigger: 'change' }],
}

const weightSum = computed(() => metrics.value.reduce((sum, m) => sum + (m.weight || 0), 0))
const isWeightValid = computed(() => Math.abs(weightSum.value - 1.0) < 0.11)

function addMetric() {
  metrics.value.push({ type: '', weight: 0.1, threshold: '', prompt_id: null })
}

function removeMetric(idx) {
  if (metrics.value.length <= 1) {
    ElMessage.warning('至少需要一个指标')
    return
  }
  metrics.value.splice(idx, 1)
}

function onMetricTypeChange(idx) {
  // Auto-set default threshold for certain metrics
  const m = metrics.value[idx]
  if (['exact_match', 'json_valid', 'contains'].includes(m.type)) {
    m.threshold = ''
  } else if (!m.threshold) {
    m.threshold = '0.8'
  }
}

async function loadOptions() {
  agentsLoading.value = true
  datasetsLoading.value = true
  try {
    const [agentsRes, datasetsRes] = await Promise.all([
      agentApi.list({ page_size: 100 }),
      datasetApi.list({ page_size: 100 }),
      promptStore.fetchPrompts({ is_active: 'true' }),
      judgeModelStore.fetchModels({ is_active: 'true' }),
    ])
    agents.value = agentsRes.results || agentsRes
    datasets.value = datasetsRes.results || datasetsRes
    // Auto-select default judge model if one exists
    const defaultModel = judgeModelStore.defaultModel
    if (defaultModel) {
      selectedJudgeModelId.value = defaultModel.id
      onJudgeModelSelect(defaultModel.id)
    }
  } catch (e) {
    ElMessage.error('加载智能体/数据集失败')
  } finally {
    agentsLoading.value = false
    datasetsLoading.value = false
  }
}

// Mapping: frontend metric key → backend {name, type, criteria}
const METRIC_MAP = {
  // Rule-based
  exact_match:   { name: 'exact_match',       type: 'rule',          criteria: '' },
  contains:      { name: 'keyword_coverage',   type: 'rule',          criteria: '' },
  regex_match:   { name: 'string_similarity',  type: 'rule',          criteria: '' },
  json_valid:    { name: 'exact_match',        type: 'rule',          criteria: '' },
  length_check:  { name: 'length_ratio',       type: 'rule',          criteria: '' },
  bleu:          { name: 'bleu',               type: 'rule',          criteria: '' },
  // LLM-as-Judge (G-Eval)
  correctness:   { name: 'correctness',   type: 'g_eval', criteria: 'Evaluate whether the response is correct and accurate compared to the expected answer.' },
  relevance:     { name: 'relevance',     type: 'g_eval', criteria: 'Evaluate whether the response is relevant to the question and directly addresses the user\'s intent.' },
  faithfulness:  { name: 'faithfulness',  type: 'g_eval', criteria: 'Evaluate whether the response is faithful to the provided context without fabrication.' },
  hallucination: { name: 'hallucination', type: 'g_eval', criteria: 'Evaluate whether the response contains hallucinated or fabricated information not supported by the context.' },
  answer_quality:{ name: 'answer_quality', type: 'g_eval', criteria: 'Evaluate the overall quality of the response including accuracy, completeness, and clarity.' },
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch { return }

  if (!isWeightValid.value) {
    ElMessage.error('指标权重总和应约为 1.0')
    return
  }

  // Build judge_model
  const judgeModel = {}
  if (selectedJudgeModelId.value) {
    judgeModel.judge_model_id = selectedJudgeModelId.value
  }
  if (judge.model) {
    judgeModel.model = judge.model
    if (judge.api_base) judgeModel.api_base = judge.api_base
    if (judge.api_key) judgeModel.api_key = judge.api_key
  }

  // Build evaluator_config — map frontend metric keys to backend format
  const evaluatorConfig = {
    metrics: metrics.value.map(m => {
      const mapping = METRIC_MAP[m.type] || { name: m.type, type: 'g_eval', criteria: '' }
      const metric = {
        name: mapping.name,
        type: mapping.type,
        weight: m.weight,
        criteria: mapping.criteria,
      }
      if (m.threshold) metric.threshold = parseFloat(m.threshold)
      if (m.prompt_id) metric.prompt_id = m.prompt_id
      return metric
    }),
  }

  const payload = {
    name: form.name,
    agent: form.agent,
    dataset: form.dataset,
    judge_model: judgeModel,
    evaluator_config: evaluatorConfig,
    parallel: form.parallel,
    limit: form.limit || null,
    conv_id_strategy: form.conv_id_strategy,
  }

  try {
    const task = await store.createTask(payload)
    ElMessage.success('任务创建成功')
    router.push(`/tasks/${task.id}`)
  } catch (e) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      const msgs = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
      ElMessage.error(msgs.join(' | '))
    } else {
      ElMessage.error(e.message || '创建任务失败')
    }
  }
}

onMounted(() => loadOptions())
</script>

<style scoped>
.task-create-page { display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; justify-content: space-between; align-items: center; }
.back-btn { color: var(--text-secondary) !important; }

.create-form { display: flex; flex-direction: column; gap: 16px; }

.section { position: relative; }
.section-title { color: var(--text-primary); font-size: 15px; margin: 0 0 4px; }
.section-desc { color: var(--text-secondary); font-size: 12px; margin: 0 0 16px; }

.option-row { display: flex; align-items: center; gap: 8px; width: 100%; }
.option-meta { margin-left: auto; color: var(--text-secondary); font-size: 11px; }

.metrics-list { display: flex; flex-direction: column; gap: 8px; }
.metric-row {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 12px;
}

.metrics-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.weight-sum { font-size: 12px; color: var(--danger); }
.weight-sum.valid { color: var(--success); }

.field-hint { color: var(--text-muted); font-size: 11px; margin-top: 4px; display: block; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}
</style>
