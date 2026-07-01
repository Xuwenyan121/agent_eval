<template>
  <div class="rules-page">
    <div class="page-toolbar">
      <h3 style="margin: 0; color: var(--text-primary)">收集规则管理</h3>
      <div class="toolbar-right">
        <el-select v-model="filterType" size="small" style="width: 160px" clearable @change="loadRules">
          <el-option label="全部类型" value="" />
          <el-option label="分数阈值" value="score_below" />
          <el-option label="高分抽查" value="score_above" />
          <el-option label="分指标阈值" value="metric_below" />
          <el-option label="边界样本" value="boundary" />
          <el-option label="随机抽样" value="random" />
          <el-option label="错误样本" value="error" />
          <el-option label="高延迟" value="high_latency" />
          <el-option label="评分分歧" value="score_variance" />
        </el-select>
        <el-button size="small" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          创建规则
        </el-button>
      </div>
    </div>

    <!-- Rules Table -->
    <div class="card" style="padding: 0; overflow: hidden">
      <el-table
        :data="rules"
        v-loading="loading"
        class="rules-table"
        :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
        row-key="id"
        empty-text=""
      >
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column label="类型" width="140">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ ruleTypeLabel(row.rule_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="参数" min-width="200">
          <template #default="{ row }">
            <span class="mono-text">{{ formatParams(row.parameters) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80" align="center">
          <template #default="{ row }">{{ row.priority }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="openTest(row)">试运行</el-button>
            <el-popconfirm title="确定删除此规则？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState v-if="!loading && rules.length === 0" icon="Setting" title="暂无收集规则" description="点击「创建规则」开始配置 BadCase 收集策略" />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingRule ? '编辑规则' : '创建规则'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="规则名称" required>
          <el-input v-model="form.name" placeholder="如：低分样本收集" />
        </el-form-item>
        <el-form-item label="规则类型" required>
          <el-select v-model="form.rule_type" placeholder="选择类型" style="width: 100%">
            <el-option label="综合分低于阈值" value="score_below" />
            <el-option label="高分抽查" value="score_above" />
            <el-option label="分指标低于阈值" value="metric_below" />
            <el-option label="分指标高分抽查" value="metric_above" />
            <el-option label="边界样本" value="boundary" />
            <el-option label="随机抽样" value="random" />
            <el-option label="错误样本" value="error" />
            <el-option label="高延迟" value="high_latency" />
            <el-option label="低延迟(疑似缓存)" value="low_latency" />
            <el-option label="评分分歧" value="score_variance" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数" required>
          <el-input
            v-model="form.parameters_str"
            type="textarea"
            :rows="4"
            placeholder='{"threshold": 0.6} 或 {"metric_name": "truthfulness", "threshold": 0.5}'
          />
          <span class="form-hint">JSON 格式。各类型参数详见文档</span>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="上限">
          <el-input-number v-model="form.max_count" :min="1" placeholder="无限制" />
          <span class="form-hint">单次最多收集数（空=不限制）</span>
        </el-form-item>
        <el-form-item label="自动收集">
          <el-switch v-model="form.auto_collect" />
          <span class="form-hint">任务完成后自动触发（需任务配置中开启）</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="规则说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ editingRule ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Test Dialog -->
    <el-dialog v-model="testVisible" title="规则试运行" width="600px" destroy-on-close>
      <el-form size="small">
        <el-form-item label="选择任务">
          <el-select v-model="testTaskId" placeholder="选择已完成的任务" style="width: 100%" filterable>
            <el-option v-for="t in testTasks" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="runTest" :loading="testing" style="margin-top: 8px">
        开始试运行
      </el-button>

      <div v-if="testResult" style="margin-top: 16px">
        <el-divider />
        <div style="margin-bottom: 8px; font-size: 13px; color: var(--text-primary)">
          匹配结果：<strong>{{ testResult.matched_count }}</strong> / {{ testResult.total_results }} 条
        </div>
        <div v-for="r in testResult.results?.slice(0, 20)" :key="r.sample_id" class="test-item">
          <span class="test-sample-id">{{ r.sample_id }}</span>
          <span class="test-score" :class="scoreClass(r.overall_score)">{{ (r.overall_score * 100).toFixed(0) }}%</span>
          <span class="test-reason">{{ r.reason }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { badcaseRuleApi, taskApi } from '@/api'
import { EmptyState } from '@/components'
import { ElMessage } from 'element-plus'

const rules = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const testVisible = ref(false)
const editingRule = ref(null)
const saving = ref(false)
const testing = ref(false)
const filterType = ref('')
const testTaskId = ref('')
const testTasks = ref([])
const testResult = ref(null)

const form = ref({
  name: '',
  rule_type: 'score_below',
  parameters_str: '{"threshold": 0.6}',
  priority: 0,
  max_count: null,
  auto_collect: false,
  description: '',
})

const RULE_TYPE_LABELS = {
  score_below: '分数阈值',
  score_above: '高分抽查',
  metric_below: '分指标阈值',
  metric_above: '指标高分抽查',
  boundary: '边界样本',
  random: '随机抽样',
  error: '错误样本',
  high_latency: '高延迟',
  low_latency: '低延迟(缓存)',
  score_variance: '评分分歧',
}

function ruleTypeLabel(type) {
  return RULE_TYPE_LABELS[type] || type
}

function formatParams(params) {
  if (!params) return '—'
  const entries = Object.entries(params).slice(0, 3)
  return entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')
}

async function loadRules() {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.rule_type = filterType.value
    const res = await badcaseRuleApi.list(params)
    rules.value = res.results || res
  } catch {
    ElMessage.error('加载规则失败')
  } finally {
    loading.value = false
  }
}

async function loadTestTasks() {
  try {
    const res = await taskApi.list({ status: 'completed', page_size: 100 })
    testTasks.value = res.results || []
  } catch { /* ignore */ }
}

function openCreate() {
  editingRule.value = null
  form.value = {
    name: '', rule_type: 'score_below', parameters_str: '{"threshold": 0.6}',
    priority: 0, max_count: null, auto_collect: false, description: '',
  }
  dialogVisible.value = true
}

function openEdit(row) {
  editingRule.value = row
  form.value = {
    name: row.name, rule_type: row.rule_type,
    parameters_str: JSON.stringify(row.parameters || {}, null, 2),
    priority: row.priority || 0, max_count: row.max_count,
    auto_collect: row.auto_collect || false, description: row.description || '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    let params
    try {
      params = JSON.parse(form.value.parameters_str)
    } catch {
      ElMessage.error('参数 JSON 格式无效')
      saving.value = false
      return
    }

    const data = {
      name: form.value.name,
      rule_type: form.value.rule_type,
      parameters: params,
      priority: form.value.priority,
      max_count: form.value.max_count || null,
      auto_collect: form.value.auto_collect,
      description: form.value.description,
    }

    if (editingRule.value) {
      await badcaseRuleApi.update(editingRule.value.id, data)
      ElMessage.success('规则已更新')
    } else {
      await badcaseRuleApi.create(data)
      ElMessage.success('规则已创建')
    }
    dialogVisible.value = false
    await loadRules()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleRule(row) {
  try {
    await badcaseRuleApi.partialUpdate(row.id, { enabled: row.enabled })
  } catch {
    row.enabled = !row.enabled
    ElMessage.error('更新失败')
  }
}

async function handleDelete(row) {
  try {
    await badcaseRuleApi.delete(row.id)
    ElMessage.success('已删除')
    await loadRules()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function openTest(row) {
  editingRule.value = row
  testResult.value = null
  testTaskId.value = ''
  testVisible.value = true
  await loadTestTasks()
}

async function runTest() {
  if (!testTaskId.value) {
    ElMessage.warning('请选择任务')
    return
  }
  testing.value = true
  try {
    const res = await badcaseRuleApi.test(editingRule.value.id, { task_id: testTaskId.value })
    testResult.value = res
  } catch {
    ElMessage.error('试运行失败')
  } finally {
    testing.value = false
  }
}

function scoreClass(score) {
  if (score >= 0.8) return 'text-success'
  if (score >= 0.5) return 'text-warning'
  return 'text-danger'
}

onMounted(() => {
  loadRules()
})
</script>

<style scoped>
.rules-page { display: flex; flex-direction: column; gap: 16px; }

.page-toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }

.rules-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: var(--border-color);
}

.mono-text { font-family: monospace; font-size: 11px; color: var(--text-secondary); }
.form-hint { font-size: 11px; color: var(--text-muted); margin-left: 4px; }

.test-item {
  display: flex; align-items: center; gap: 12px;
  padding: 6px 10px; border-radius: 6px;
  background: var(--bg-card); border: 1px solid var(--border-color);
  margin-bottom: 4px;
}
.test-sample-id { font-family: monospace; font-size: 12px; color: var(--text-secondary); min-width: 60px; }
.test-score { font-weight: 700; font-size: 13px; min-width: 45px; }
.test-reason { font-size: 11px; color: var(--text-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.text-success { color: #00D68F; }
.text-warning { color: #FFAA00; }
.text-danger { color: #FF3D71; }
</style>