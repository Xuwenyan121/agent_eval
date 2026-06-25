<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- Tab 1: Metric Registry -->
      <el-tab-pane label="指标注册表" name="metrics">
        <div class="toolbar">
          <div class="toolbar-left">
            <el-select v-model="filterCategory" placeholder="分类" clearable style="width: 180px" @change="loadMetrics">
              <el-option label="业务维度" value="business_dim" />
              <el-option label="ML 指标" value="ml_metric" />
              <el-option label="多模态" value="multimodal" />
            </el-select>
            <el-select v-model="filterType" placeholder="类型" clearable style="width: 150px" @change="loadMetrics">
              <el-option label="G-Eval (LLM)" value="g_eval" />
              <el-option label="规则类" value="rule" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </div>
          <div class="toolbar-right">
            <span class="count-badge">{{ store.total }} 个指标</span>
          </div>
        </div>

        <div class="card" style="padding: 0; overflow: hidden">
          <el-table
            :data="store.definitions"
            v-loading="store.loading"
            class="metric-table"
            :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
            row-key="id"
            empty-text=""
          >
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="expand-content">
                  <div class="expand-row" v-if="row.criteria">
                    <h5>评分标准</h5>
                    <pre class="criteria-text">{{ row.criteria }}</pre>
                  </div>
                  <div class="expand-row" v-if="row.rule_class">
                    <h5>规则类</h5>
                    <code class="code-text">{{ row.rule_class }}</code>
                  </div>
                  <div class="expand-row" v-if="row.rule_params && Object.keys(row.rule_params).length">
                    <h5>规则参数</h5>
                    <pre class="json-text">{{ JSON.stringify(row.rule_params, null, 2) }}</pre>
                  </div>
                  <div class="expand-row" v-if="row.default_params && Object.keys(row.default_params).length">
                    <h5>默认参数</h5>
                    <pre class="json-text">{{ JSON.stringify(row.default_params, null, 2) }}</pre>
                  </div>
                  <div class="expand-row" v-if="row.description">
                    <h5>描述</h5>
                    <p class="desc-text">{{ row.description }}</p>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="display_name" label="指标" min-width="180">
              <template #default="{ row }">
                <div class="metric-info">
                  <span class="metric-name">{{ row.display_name }}</span>
                  <span class="metric-id">{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="160">
              <template #default="{ row }">
                <el-tag size="small" :type="categoryTag(row.category)" effect="plain">
                  {{ categoryLabel(row.category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="130">
              <template #default="{ row }">
                <el-tag size="small" :type="typeTag(row.type)" effect="plain">
                  {{ typeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="weight" label="权重" width="80" align="center">
              <template #default="{ row }">
                <span class="accent-text">{{ row.weight }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="default_threshold" label="阈值" width="100" align="center">
              <template #default="{ row }">
                <span>{{ row.default_threshold }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用" width="80" align="center">
              <template #default="{ row }">
                <el-icon :style="{ color: row.enabled ? '#00D68F' : '#FF3D71' }">
                  <component :is="row.enabled ? 'CircleCheck' : 'CircleClose'" />
                </el-icon>
              </template>
            </el-table-column>
          </el-table>

          <EmptyState
            v-if="!store.loading && store.definitions.length === 0"
            icon="Coin"
            title="暂无注册指标"
            description="指标定义通过 Django 管理后台或数据库迁移进行管理。"
          />
        </div>
      </el-tab-pane>

      <!-- Tab 2: Metric Playground -->
      <el-tab-pane label="指标调试" name="playground">
        <div class="playground-grid">
          <!-- Mode Selector -->
          <div class="card mode-selector-card">
            <h4 class="section-title">调试模式</h4>
            <el-radio-group v-model="pgMode" size="large">
              <el-radio-button value="rule">
                <el-icon style="vertical-align: -2px; margin-right: 4px"><SetUp /></el-icon>
                规则类指标
              </el-radio-button>
              <el-radio-button value="llm_judge">
                <el-icon style="vertical-align: -2px; margin-right: 4px"><ChatLineRound /></el-icon>
                LLM 裁判 Prompt
              </el-radio-button>
            </el-radio-group>
          </div>

          <!-- Config Section (Rule Mode) -->
          <div class="card" v-if="pgMode === 'rule'">
            <h4 class="section-title">指标配置</h4>
            <p class="section-desc">定义待测试的指标，至少需要一个指标和一个样本。</p>
            <div class="config-list">
              <div v-for="(m, idx) in pgMetrics" :key="idx" class="config-row">
                <el-select v-model="m.type" placeholder="选择指标" style="width: 180px" filterable>
                  <el-option
                    v-for="rm in store.ruleMetrics"
                    :key="rm.name"
                    :label="rm.display_name || rm.name"
                    :value="rm.name"
                  >
                    <span>{{ rm.display_name || rm.name }}</span>
                    <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px">
                      ({{ rm.name }})
                    </span>
                  </el-option>
                </el-select>
                <el-input-number v-model="m.weight" :min="0" :max="1" :step="0.1" :precision="1" size="small" controls-position="right" style="width: 110px" />
                <el-input v-model="m.threshold" placeholder="Threshold" style="width: 110px" />
                <el-button text type="danger" @click="pgMetrics.splice(idx, 1)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>
            <el-button size="small" style="margin-top: 8px" @click="pgMetrics.push({ type: '', weight: 0.5, threshold: '0.8' })">
              <el-icon><Plus /></el-icon>
              添加指标
            </el-button>
          </div>

          <!-- Prompt Selector (LLM Judge Mode) -->
          <div class="card" v-if="pgMode === 'llm_judge'">
            <h4 class="section-title">选择 Prompt 模板</h4>
            <p class="section-desc">从 Prompt 库中选择一个裁判 Prompt 进行调试，或使用自定义 Criteria。</p>
            <el-select
              v-model="pgPromptId"
              placeholder="选择 Prompt 模板"
              clearable
              filterable
              style="width: 100%"
              @clear="pgPromptId = null"
            >
              <el-option
                v-for="p in promptStore.prompts"
                :key="p.id"
                :label="`${p.display_name} (${p.category})`"
                :value="p.id"
              >
                <div style="display: flex; justify-content: space-between; align-items: center">
                  <span>{{ p.display_name }}</span>
                  <el-tag size="small" effect="plain" type="info">{{ p.category }}</el-tag>
                </div>
              </el-option>
            </el-select>
            <!-- Show prompt details when selected -->
            <div v-if="selectedPromptObj" class="prompt-preview-box">
              <div class="preview-label">
                <el-icon><Document /></el-icon>
                <span>{{ selectedPromptObj.display_name }}</span>
                <el-tag size="small" effect="plain">{{ selectedPromptObj.category }}</el-tag>
              </div>
              <div class="preview-criteria" v-if="selectedPromptObj.criteria">
                <h5>评分标准</h5>
                <pre>{{ selectedPromptObj.criteria }}</pre>
              </div>
              <div class="preview-steps" v-if="selectedPromptObj.evaluation_steps?.length">
                <h5>评估步骤</h5>
                <ol>
                  <li v-for="(step, i) in selectedPromptObj.evaluation_steps" :key="i">{{ step }}</li>
                </ol>
              </div>
            </div>
          </div>

          <!-- Sample Section -->
          <div class="card">
            <h4 class="section-title">测试样本</h4>
            <el-form label-position="top">
              <el-form-item label="输入">
                <el-input v-model="pgSample.input" type="textarea" :rows="2" placeholder='{"query": "退货政策是什么？"}' />
              </el-form-item>
              <el-form-item label="实际输出">
                <el-input v-model="pgSample.actual_output" type="textarea" :rows="2" placeholder="退货政策为30天内..." />
              </el-form-item>
              <el-form-item label="期望输出">
                <el-input v-model="pgSample.expected_output" type="textarea" :rows="2" placeholder="购买后30天内可退货。" />
              </el-form-item>
            </el-form>
          </div>

          <!-- Judge Model (optional for rule, required for LLM judge) -->
          <div class="card">
            <h4 class="section-title">
              裁判模型
              <el-tag v-if="pgMode === 'llm_judge'" size="small" type="danger" effect="plain" style="margin-left: 8px">必填</el-tag>
              <el-tag v-else size="small" type="info" effect="plain" style="margin-left: 8px">可选</el-tag>
            </h4>
            <el-select
              v-model="pgJudgeModelId"
              placeholder="选择预设模型（或手动填写下方）"
              clearable
              filterable
              style="width: 100%; margin-bottom: 10px"
              @change="onPgJudgeModelSelect"
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
            <el-row :gutter="12">
              <el-col :span="8">
                <el-input v-model="pgJudge.model" placeholder="Model (e.g. gpt-4o)" />
              </el-col>
              <el-col :span="8">
                <el-input v-model="pgJudge.api_base" placeholder="API Base URL" />
              </el-col>
              <el-col :span="8">
                <el-input v-model="pgJudge.api_key" placeholder="API Key" type="password" show-password />
              </el-col>
            </el-row>
          </div>

          <!-- Run Button -->
          <el-button
            class="btn-gradient"
            :loading="pgMode === 'llm_judge' ? pgPromptLoading : store.loading"
            @click="handleDryRun"
            style="width: fit-content"
          >
            <el-icon><VideoPlay /></el-icon>
            {{ pgMode === 'llm_judge' ? '运行 Prompt 调试' : '运行调试测试' }}
          </el-button>

          <!-- Rule Mode Results -->
          <div class="card" v-if="pgMode === 'rule' && store.dryRunResult">
            <h4 class="section-title">调试结果</h4>

            <!-- Validation -->
            <div class="validation-box" v-if="store.dryRunResult.validation">
              <el-tag :type="store.dryRunResult.validation.valid ? 'success' : 'danger'" size="small">
                {{ store.dryRunResult.validation.valid ? '配置有效' : '配置无效' }}
              </el-tag>
              <span v-if="store.dryRunResult.validation.errors?.length" class="error-text">
                {{ store.dryRunResult.validation.errors.join(', ') }}
              </span>
            </div>

            <!-- Per-sample results -->
            <div class="dryrun-results" v-if="store.dryRunResult.results">
              <div v-for="(sampleResult, sIdx) in (store.dryRunResult.results.results || [])" :key="sIdx" class="sample-result">
                <div class="sample-header">
                  <span class="sample-label">样本 {{ sIdx + 1 }}</span>
                  <span class="overall-score" :class="(sampleResult.overall_score || 0) >= 0.8 ? 'success' : (sampleResult.overall_score || 0) >= 0.5 ? 'warning' : 'danger'">
                    得分：{{ ((sampleResult.overall_score || 0) * 100).toFixed(0) }}%
                  </span>
                </div>
                <div class="metric-results" v-if="sampleResult.metrics">
                  <div v-for="(val, name) in sampleResult.metrics" :key="name" class="dryrun-metric">
                    <span class="dm-name">{{ name }}</span>
                    <el-tag :type="val.passed ? 'success' : 'danger'" size="small" effect="plain">
                      {{ ((val.score || 0) * 100).toFixed(0) }}%
                    </el-tag>
                    <span class="dm-reason" v-if="val.reason">{{ val.reason }}</span>
                  </div>
                </div>
              </div>

              <!-- Summary -->
              <div v-if="store.dryRunResult.results.summary" class="dryrun-summary">
                <span>平均得分：{{ ((store.dryRunResult.results.summary.avg_score || 0) * 100).toFixed(1) }}%</span>
                <span style="margin-left: 16px">通过率：{{ ((store.dryRunResult.results.summary.pass_rate || 0) * 100).toFixed(0) }}%</span>
              </div>

              <!-- Errors -->
              <div v-if="store.dryRunResult.results.errors?.length" class="dryrun-errors">
                <div v-for="(err, eIdx) in store.dryRunResult.results.errors" :key="eIdx" class="error-item">
                  <el-tag type="danger" size="small">错误</el-tag>
                  <span class="error-text">{{ err.error || JSON.stringify(err) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- LLM Judge Prompt Results -->
          <div class="card" v-if="pgMode === 'llm_judge' && pgPromptResult">
            <h4 class="section-title">Prompt 调试结果</h4>
            <div class="prompt-result-grid">
              <div class="prompt-result-stat">
                <span class="stat-label">评分</span>
                <span class="stat-value score" :class="pgPromptResult.score >= 0.8 ? 'success' : pgPromptResult.score >= 0.5 ? 'warning' : 'danger'">
                  {{ (pgPromptResult.score * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="prompt-result-stat" v-if="pgPromptResult.latency_ms">
                <span class="stat-label">耗时</span>
                <span class="stat-value">{{ (pgPromptResult.latency_ms / 1000).toFixed(2) }}s</span>
              </div>
              <div class="prompt-result-stat" v-if="pgPromptResult.tokens_used">
                <span class="stat-label">Token 使用</span>
                <span class="stat-value mono">
                  {{ pgPromptResult.tokens_used.prompt || 0 }} / {{ pgPromptResult.tokens_used.completion || 0 }}
                </span>
              </div>
            </div>
            <div class="prompt-reason-box" v-if="pgPromptResult.reason">
              <h5>评估理由</h5>
              <p>{{ pgPromptResult.reason }}</p>
            </div>
            <div class="prompt-rendered-box" v-if="pgPromptResult.rendered_prompt">
              <h5>渲染后的 Prompt</h5>
              <pre>{{ pgPromptResult.rendered_prompt }}</pre>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: System Info -->
      <el-tab-pane label="系统信息" name="system">
        <div class="card info-card">
          <h4 class="section-title">平台信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">平台</span>
              <span class="info-value">智能体评测平台</span>
            </div>
            <div class="info-item">
              <span class="info-label">版本</span>
              <span class="info-value accent">v3.2</span>
            </div>
            <div class="info-item">
              <span class="info-label">API 基础地址</span>
              <span class="info-value mono">{{ apiBaseUrl }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">前端框架</span>
              <span class="info-value">Vue 3 + Vite + Element Plus</span>
            </div>
            <div class="info-item">
              <span class="info-label">后端框架</span>
              <span class="info-value">Django 5 + DRF</span>
            </div>
            <div class="info-item">
              <span class="info-label">任务执行器</span>
              <span class="info-value">Celery + Redis</span>
            </div>
            <div class="info-item">
              <span class="info-label">数据库</span>
              <span class="info-value">PostgreSQL / SQLite（开发）</span>
            </div>
            <div class="info-item">
              <span class="info-label">追踪</span>
              <span class="info-value">MLflow</span>
            </div>
          </div>
        </div>

        <div class="card info-card">
          <h4 class="section-title">快捷链接</h4>
          <div class="links-grid">
            <a class="link-card" @click="$router.push('/dashboard')">
              <el-icon :size="20"><DataAnalysis /></el-icon>
              <span>仪表盘</span>
            </a>
            <a class="link-card" @click="$router.push('/agents')">
              <el-icon :size="20"><Monitor /></el-icon>
              <span>智能体</span>
            </a>
            <a class="link-card" @click="$router.push('/datasets')">
              <el-icon :size="20"><FolderOpened /></el-icon>
              <span>数据集</span>
            </a>
            <a class="link-card" @click="$router.push('/tasks')">
              <el-icon :size="20"><SetUp /></el-icon>
              <span>评测任务</span>
            </a>
            <a class="link-card" @click="$router.push('/reports')">
              <el-icon :size="20"><Document /></el-icon>
              <span>评测报告</span>
            </a>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useMetricStore } from '@/stores/metrics'
import { usePromptStore } from '@/stores/prompts'
import { useJudgeModelStore } from '@/stores/judgeModels'
import { promptApi } from '@/api'
import { EmptyState } from '@/components'
import { ElMessage } from 'element-plus'

const store = useMetricStore()
const promptStore = usePromptStore()
const judgeModelStore = useJudgeModelStore()
const activeTab = ref('metrics')

// Filters
const filterCategory = ref('')
const filterType = ref('')

// API base URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// Labels
const categoryLabels = { business_dim: '业务维度', ml_metric: 'ML 指标', multimodal: '多模态' }
const categoryLabel = (c) => categoryLabels[c] || c
const categoryTag = (c) => ({ business_dim: 'primary', ml_metric: 'success', multimodal: 'warning' })[c] || 'info'
const typeLabels = { g_eval: 'G-Eval (LLM)', rule: '规则类', custom: '自定义', deepeval_builtin: 'DeepEval' }
const typeLabel = (t) => typeLabels[t] || t
const typeTag = (t) => ({ g_eval: 'primary', rule: 'success', custom: 'warning' })[t] || 'info'

// Playground state
const pgMode = ref('rule') // 'rule' or 'llm_judge'
const pgMetrics = ref([{ type: 'exact_match', weight: 0.5, threshold: '0.8' }])
const pgSample = reactive({ input: '', actual_output: '', expected_output: '' })
const pgJudge = reactive({ model: '', api_base: '', api_key: '' })
const pgPromptId = ref(null)
const pgPromptResult = ref(null)
const pgPromptLoading = ref(false)
const pgJudgeModelId = ref(null)

function onPgJudgeModelSelect(id) {
  if (!id) {
    pgJudge.model = ''
    pgJudge.api_base = ''
    pgJudge.api_key = ''
    return
  }
  const preset = judgeModelStore.models.find(m => m.id === id)
  if (preset) {
    pgJudge.model = preset.model
    pgJudge.api_base = preset.api_base || ''
    pgJudge.api_key = ''
  }
}

const selectedPromptObj = computed(() => {
  if (!pgPromptId.value) return null
  return promptStore.prompts.find(p => p.id === pgPromptId.value) || null
})

async function loadMetrics() {
  const params = {}
  if (filterCategory.value) params.category = filterCategory.value
  if (filterType.value) params.type = filterType.value
  await store.fetchDefinitions(params)
}

async function handleDryRun() {
  // LLM Judge mode: use prompt dry-run endpoint
  if (pgMode.value === 'llm_judge') {
    return handlePromptDryRun()
  }

  // Rule mode: use metric dry-run endpoint
  const metrics = pgMetrics.value
    .filter(m => m.type)
    .map(m => {
      const metric = { name: m.type, type: 'rule', weight: m.weight }
      if (m.threshold) metric.threshold = parseFloat(m.threshold)
      return metric
    })

  if (!metrics.length) {
    ElMessage.warning('请添加至少一个指标')
    return
  }
  if (!pgSample.input || !pgSample.actual_output) {
    ElMessage.warning('请输入输入和实际输出')
    return
  }

  const payload = {
    metrics,
    samples: [{
      input: pgSample.input,
      actual_output: pgSample.actual_output,
      expected_output: pgSample.expected_output,
    }],
  }

  // Add judge model if configured
  if (pgJudge.model) {
    payload.judge_model = { model: pgJudge.model }
    if (pgJudge.api_base) payload.judge_model.api_base = pgJudge.api_base
    if (pgJudge.api_key) payload.judge_model.api_key = pgJudge.api_key
  }

  try {
    await store.dryRun(payload)
    ElMessage.success('调试测试完成')
  } catch (e) {
    const data = e.response?.data
    if (data?.error) {
      ElMessage.error(data.error)
    } else {
      ElMessage.error(e.message || '调试测试失败')
    }
  }
}

async function handlePromptDryRun() {
  if (!pgSample.input && !pgSample.actual_output) {
    ElMessage.warning('请输入输入或实际输出')
    return
  }
  if (!pgJudge.model) {
    ElMessage.warning('请配置裁判模型')
    return
  }

  const payload = {
    prompt_id: pgPromptId.value || null,
    criteria: '',
    evaluation_steps: [],
    sample: {
      input: pgSample.input,
      actual_output: pgSample.actual_output,
      expected_output: pgSample.expected_output,
    },
    judge_model: { model: pgJudge.model },
  }
  if (pgJudge.api_base) payload.judge_model.api_base = pgJudge.api_base
  if (pgJudge.api_key) payload.judge_model.api_key = pgJudge.api_key

  pgPromptLoading.value = true
  pgPromptResult.value = null
  try {
    pgPromptResult.value = await promptApi.dryRun(payload)
    ElMessage.success('Prompt 调试完成')
  } catch (e) {
    const msg = e.response?.data?.error || e.message
    ElMessage.error(msg || 'Prompt 调试失败')
  } finally {
    pgPromptLoading.value = false
  }
}

onMounted(async () => {
  await loadMetrics()
  await store.fetchTypes()
  await Promise.all([
    promptStore.fetchPrompts({ is_active: 'true' }),
    judgeModelStore.fetchModels({ is_active: 'true' }),
  ])
  // Auto-select default judge model
  const defaultModel = judgeModelStore.defaultModel
  if (defaultModel) {
    pgJudgeModelId.value = defaultModel.id
    onPgJudgeModelSelect(defaultModel.id)
  }
})
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 16px; }
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0; }

.settings-tabs :deep(.el-tabs__item) { color: var(--text-secondary); font-size: 13px; }
.settings-tabs :deep(.el-tabs__item.is-active) { color: var(--accent-start); }
.settings-tabs :deep(.el-tabs__active-bar) { background: var(--accent-start); }
.settings-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-color); }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}
.toolbar-left { display: flex; gap: 10px; }
.count-badge {
  background: rgba(108, 92, 231, 0.15);
  color: var(--accent-start);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
}

.metric-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
}
.metric-info { display: flex; flex-direction: column; gap: 2px; }
.metric-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.metric-id { font-size: 11px; color: var(--text-secondary); font-family: monospace; }
.accent-text { color: var(--accent-start); font-weight: 600; }

.expand-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 20px;
}
.expand-row h5 { font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin: 0 0 4px; }
.criteria-text { color: var(--text-primary); font-size: 12px; white-space: pre-wrap; margin: 0; background: var(--bg-card); padding: 8px; border-radius: 6px; }
.code-text { color: var(--accent-start); font-size: 12px; background: var(--bg-card); padding: 4px 8px; border-radius: 4px; }
.json-text { color: var(--text-primary); font-size: 12px; font-family: monospace; background: var(--bg-card); padding: 8px; border-radius: 6px; margin: 0; white-space: pre-wrap; }
.desc-text { color: var(--text-secondary); font-size: 12px; margin: 0; }

/* Playground */
.playground-grid { display: flex; flex-direction: column; gap: 16px; }
.section-title { color: var(--text-primary); font-size: 14px; margin: 0 0 4px; }
.section-desc { color: var(--text-secondary); font-size: 12px; margin: 0 0 12px; }

.config-list { display: flex; flex-direction: column; gap: 6px; }
.config-row { display: flex; gap: 8px; align-items: center; }

.validation-box {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.error-text { color: var(--danger); font-size: 12px; }

.dryrun-results { display: flex; flex-direction: column; gap: 12px; }
.sample-result {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
}
.sample-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.sample-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; }
.overall-score { font-size: 14px; font-weight: 700; }
.overall-score.success { color: var(--success); }
.overall-score.warning { color: var(--warning); }
.overall-score.danger { color: var(--danger); }

.metric-results { display: flex; flex-direction: column; gap: 6px; }
.dryrun-metric {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.dm-name { color: var(--text-secondary); min-width: 100px; text-transform: capitalize; }
.dm-reason { color: var(--text-muted); font-size: 11px; }

.dryrun-summary {
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
}

.dryrun-errors {
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--danger);
  border-radius: 8px;
}
.error-item { display: flex; align-items: center; gap: 8px; }
.error-text { color: var(--danger); font-size: 12px; }

/* System Info */
.info-card { background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-input) 100%); }
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.accent { color: var(--accent-start); font-weight: 600; }
.info-value.mono { font-family: monospace; font-size: 12px; }

.links-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.link-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.link-card:hover { border-color: rgba(108, 92, 231, 0.4); }
.link-card .el-icon { color: var(--accent-start); }

/* Mode Selector */
.mode-selector-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mode-selector-card :deep(.el-radio-button__inner) {
  background: var(--bg-card);
  border-color: var(--border-color);
  color: var(--text-secondary);
}
.mode-selector-card :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(108, 92, 231, 0.15);
  border-color: var(--accent-start);
  color: var(--accent-start);
  box-shadow: -1px 0 0 0 var(--accent-start);
}

/* Prompt Preview Box */
.prompt-preview-box {
  margin-top: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
}
.preview-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 10px;
}
.preview-label .el-icon { color: var(--accent-start); }
.preview-criteria h5, .preview-steps h5 {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin: 0 0 6px;
}
.preview-criteria pre {
  color: var(--text-primary);
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0 0 10px;
  background: var(--bg-input);
  padding: 8px;
  border-radius: 6px;
}
.preview-steps ol {
  margin: 0 0 4px;
  padding-left: 20px;
  color: var(--text-primary);
  font-size: 12px;
}
.preview-steps li { margin-bottom: 4px; }

/* Prompt Dry-Run Results */
.prompt-result-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.prompt-result-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.stat-value.score.success { color: var(--success); }
.stat-value.score.warning { color: var(--warning); }
.stat-value.score.danger { color: var(--danger); }
.stat-value.mono { font-family: monospace; font-size: 14px; }

.prompt-reason-box, .prompt-rendered-box {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 10px;
}
.prompt-reason-box h5, .prompt-rendered-box h5 {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin: 0 0 8px;
}
.prompt-reason-box p { color: var(--text-primary); font-size: 13px; margin: 0; line-height: 1.6; }
.prompt-rendered-box pre {
  color: var(--text-primary);
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
  background: var(--bg-input);
  padding: 10px;
  border-radius: 6px;
  max-height: 300px;
  overflow-y: auto;
}
</style>
