<template>
  <div class="report-detail-page">
    <!-- Header -->
    <div class="page-header">
      <el-button text @click="$router.push('/reports')" style="color: var(--text-secondary)">
        <el-icon><ArrowLeft /></el-icon>
        返回报告列表
      </el-button>
      <div class="header-actions" v-if="task">
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出 JSONL
        </el-button>
        <el-button @click="$router.push(`/tasks/${taskId}`)">
          <el-icon><SetUp /></el-icon>
          任务详情
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else-if="task">
      <!-- Summary Cards -->
      <div class="summary-row">
        <div class="card summary-card">
          <div class="summary-icon score-icon">
            <el-icon :size="20"><DataAnalysis /></el-icon>
          </div>
          <div class="summary-content">
            <span class="summary-num" :class="scoreClass(task.average_score)">
              {{ task.average_score != null ? (task.average_score * 100).toFixed(0) + '%' : '—' }}
            </span>
            <span class="summary-label">综合得分</span>
          </div>
        </div>
        <div class="card summary-card">
          <div class="summary-icon result-icon">
            <el-icon :size="20"><Document /></el-icon>
          </div>
          <div class="summary-content">
            <span class="summary-num">{{ task.result_count ?? 0 }}</span>
            <span class="summary-label">总结果数</span>
          </div>
        </div>
        <div class="card summary-card">
          <div class="summary-icon badcase-icon">
            <el-icon :size="20"><WarningFilled /></el-icon>
          </div>
          <div class="summary-content">
            <span class="summary-num" :class="(task.badcase_count ?? 0) > 0 ? 'danger' : ''">
              {{ task.badcase_count ?? 0 }}
            </span>
            <span class="summary-label">Bad Case 数</span>
          </div>
        </div>
        <div class="card summary-card">
          <div class="summary-icon time-icon">
            <el-icon :size="20"><Timer /></el-icon>
          </div>
          <div class="summary-content">
            <span class="summary-num">{{ duration }}</span>
            <span class="summary-label">耗时</span>
          </div>
        </div>
      </div>

      <!-- Task Info + Metric Breakdown -->
      <div class="info-row">
        <div class="card" style="flex: 1">
          <h4 class="section-title">任务信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">名称</span>
              <span class="info-value">{{ task.name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">智能体</span>
              <span class="info-value link" @click="$router.push(`/agents/${task.agent}/edit`)">{{ task.agent_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">数据集</span>
              <span class="info-value link" @click="$router.push(`/datasets/${task.dataset}`)">{{ task.dataset_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">裁判模型</span>
              <span class="info-value">{{ task.judge_model?.model || '无' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">完成时间</span>
              <span class="info-value">{{ formatDate(task.completed_at) }}</span>
            </div>
          </div>
        </div>

        <div class="card" style="flex: 1" v-if="metricAverages.length">
          <h4 class="section-title">指标明细</h4>
          <div class="metric-bars">
            <div v-for="m in metricAverages" :key="m.name" class="metric-bar-row">
              <span class="metric-name">{{ m.name }}</span>
              <div class="metric-bar-wrap">
                <div class="metric-bar" :style="{ width: (m.score * 100) + '%' }" :class="barClass(m.score)"></div>
              </div>
              <span class="metric-score">{{ (m.score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Results Table -->
      <div class="card" style="padding: 0; overflow: hidden">
        <div class="results-toolbar">
          <h4 style="margin: 0; color: var(--text-primary); font-size: 14px">
            评测结果
            <span class="count-badge">{{ resultStore.pagination.count }}</span>
          </h4>
          <div class="toolbar-right">
            <el-input v-model="searchResult" placeholder="搜索 sample_id..." size="small" clearable style="width: 180px" />
            <el-select v-model="filterBadcase" size="small" style="width: 130px" clearable @change="currentPage = 1; loadResults()">
              <el-option label="全部结果" value="" />
              <el-option label="仅 Bad Case" value="true" />
              <el-option label="仅通过" value="false" />
            </el-select>
            <el-select v-model="sortByScore" size="small" style="width: 130px" @change="currentPage = 1; loadResults()">
              <el-option label="分数：低→高" value="score" />
              <el-option label="分数：高→低" value="-score" />
              <el-option label="最新优先" value="" />
            </el-select>
          </div>
        </div>

        <el-table
          :data="filteredResults"
          v-loading="resultStore.loading"
          class="result-table"
          :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
          row-key="id"
          empty-text=""
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-content">
                <div class="expand-section expand-section--full">
                  <h5>输入</h5>
                  <pre class="json-block json-input" v-html="highlightJson(row.input)"></pre>
                </div>
                <div class="expand-section expand-section--full">
                  <h5>期望输出</h5>
                  <pre class="json-block json-output">{{ formatOutput(row.expected_output) }}</pre>
                </div>
                <div class="expand-section expand-section--full">
                  <h5>实际输出</h5>
                  <pre class="json-block json-output" :class="{ 'output-match': outputsMatch(row), 'output-diff': !outputsMatch(row) }">{{ formatOutput(row.actual_output) }}</pre>
                </div>
                <div class="expand-section expand-section--full" v-if="row.metric_results">
                  <h5>指标结果</h5>
                  <div class="metric-chips">
                    <div v-for="(val, key) in row.metric_results" :key="key" class="metric-chip" :class="val.passed ? 'pass' : 'fail'">
                      <span class="chip-name">{{ key }}</span>
                      <span class="chip-score">{{ ((val.score || 0) * 100).toFixed(0) }}%</span>
                      <span class="chip-reason" v-if="val.reason">{{ val.reason }}</span>
                    </div>
                  </div>
                </div>
                <div class="expand-section" v-if="row.error">
                  <h5 style="color: #FF3D71">错误</h5>
                  <pre class="json-block error-block">{{ row.error }}</pre>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="sample_id" label="样本 ID" width="120">
            <template #default="{ row }">
              <span class="sample-id">{{ row.sample_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="overall_score" label="得分" width="100" sortable>
            <template #default="{ row }">
              <div class="score-cell">
                <span class="score-dot" :class="barClass(row.overall_score)"></span>
                <span :class="scoreTextClass(row.overall_score)">{{ (row.overall_score * 100).toFixed(0) }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_badcase ? 'danger' : 'success'" size="small" effect="plain">
                {{ row.is_badcase ? 'Bad Case' : '通过' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟" width="90" align="center">
            <template #default="{ row }">
              <span class="text-muted">{{ row.latency_ms ? row.latency_ms + 'ms' : '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Trace" width="70" align="center">
            <template #default="{ row }">
              <el-button
                v-if="row.trace_id"
                text size="small"
                @click.stop="$router.push(`/traces/${row.trace_id}`)"
                style="color: var(--accent-start)"
                title="查看 Trace"
              >
                <el-icon><Connection /></el-icon>
              </el-button>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="得分明细" min-width="200">
            <template #default="{ row }">
              <div class="mini-bars" v-if="row.score_breakdown?.length">
                <div v-for="m in row.score_breakdown.slice(0, 5)" :key="m.name" class="mini-bar-item" :title="`${m.name}: ${(m.score * 100).toFixed(0)}%`">
                  <div class="mini-bar" :style="{ width: (m.score * 100) + '%' }" :class="barClass(m.score)"></div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              <span class="text-muted">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
        </el-table>

        <EmptyState
          v-if="!resultStore.loading && filteredResults.length === 0"
          icon="Document"
          title="暂无结果"
          description="该任务没有评测结果。"
        />

        <!-- Pagination -->
        <div class="pagination-wrap" v-if="resultStore.pagination.count > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="resultStore.pagination.count"
            layout="prev, pager, next, total"
            background
            @current-change="loadResults"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'
import { useResultStore } from '@/stores/results'
import { formatDate } from '@/utils'
import { EmptyState } from '@/components'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const resultStore = useResultStore()

const taskId = route.params.id
const loading = ref(true)
const currentPage = ref(1)
const pageSize = 20
const searchResult = ref('')
const filterBadcase = ref('')
const sortByScore = ref('-score')

const task = computed(() => taskStore.currentTask)

const duration = computed(() => {
  if (!task.value?.started_at || !task.value?.completed_at) return '—'
  const ms = new Date(task.value.completed_at) - new Date(task.value.started_at)
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${Math.round(ms / 1000)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
})

const metricAverages = computed(() => {
  const ma = task.value?.summary?.metric_averages
  if (!ma) return []
  return Object.entries(ma)
    .map(([name, score]) => ({ name, score }))
    .sort((a, b) => b.score - a.score)
})

const filteredResults = computed(() => {
  let list = resultStore.results
  if (searchResult.value) {
    const q = searchResult.value.toLowerCase()
    list = list.filter(r => r.sample_id?.toLowerCase().includes(q))
  }
  return list
})

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
}

function scoreTextClass(score) {
  if (score >= 0.8) return 'text-success'
  if (score >= 0.5) return 'text-warning'
  return 'text-danger'
}

function barClass(score) {
  if (score >= 0.8) return 'bar-success'
  if (score >= 0.5) return 'bar-warning'
  return 'bar-danger'
}

function formatJson(val) {
  if (!val) return '—'
  try {
    const parsed = typeof val === 'string' ? JSON.parse(val) : val
    return JSON.stringify(parsed, null, 2)
  } catch {
    return String(val)
  }
}

function formatOutput(val) {
  if (!val) return '—'
  // If it's a JSON object/string, try to extract the text content
  try {
    const parsed = typeof val === 'string' ? JSON.parse(val) : val
    if (typeof parsed === 'object' && parsed !== null) {
      // Extract text fields
      const text = parsed.expected_output || parsed.output || parsed.answer || parsed.text
      if (text) return String(text)
      return JSON.stringify(parsed, null, 2)
    }
    return String(parsed)
  } catch {
    return String(val)
  }
}

function highlightJson(val) {
  if (!val) return '—'
  let str
  try {
    const parsed = typeof val === 'string' ? JSON.parse(val) : val
    str = JSON.stringify(parsed, null, 2)
  } catch {
    str = String(val)
  }
  // Simple syntax highlighting
  return str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/("[^"]*")\s*:/g, '<span class="json-key">$1</span>:')
    .replace(/:\s*("[^"]*")/g, ': <span class="json-str">$1</span>')
    .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-num">$1</span>')
    .replace(/:\s*(true|false|null)/g, ': <span class="json-bool">$1</span>')
}

function outputsMatch(row) {
  if (!row.expected_output || !row.actual_output) return false
  const exp = typeof row.expected_output === 'string' ? row.expected_output.trim() : JSON.stringify(row.expected_output).trim()
  const act = typeof row.actual_output === 'string' ? row.actual_output.trim() : JSON.stringify(row.actual_output).trim()
  return exp === act
}

async function loadTask() {
  loading.value = true
  try {
    await taskStore.fetchTask(taskId)
  } catch {
    ElMessage.error('加载报告失败')
    router.push('/reports')
  } finally {
    loading.value = false
  }
}

async function loadResults() {
  const params = { task: taskId, page: currentPage.value, page_size: pageSize }
  if (filterBadcase.value === 'true') params.is_badcase = true
  if (filterBadcase.value === 'false') params.is_badcase = false
  if (sortByScore.value === 'score') params.ordering = 'overall_score'
  else if (sortByScore.value === '-score') params.ordering = '-overall_score'
  await resultStore.fetchResults(params)
}

async function handleExport() {
  try {
    const blob = await resultStore.exportBadcases({ task: taskId })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.value?.name || 'results'}_export.jsonl`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出已下载')
  } catch {
    ElMessage.error('导出结果失败')
  }
}

onMounted(async () => {
  await loadTask()
  if (task.value) await loadResults()
})
</script>

<style scoped>
.report-detail-page { display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 8px; }

.loading-wrap { padding: 20px; }

/* Summary Cards */
.summary-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.summary-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px !important;
}
.summary-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.score-icon { background: rgba(108, 92, 231, 0.15); color: var(--accent-start); }
.result-icon { background: rgba(0, 214, 143, 0.15); color: #00D68F; }
.badcase-icon { background: rgba(255, 61, 113, 0.15); color: #FF3D71; }
.time-icon { background: rgba(255, 170, 0, 0.15); color: #FFAA00; }

.summary-content { display: flex; flex-direction: column; gap: 2px; }
.summary-num { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.summary-num.success { color: #00D68F; }
.summary-num.warning { color: #FFAA00; }
.summary-num.danger { color: #FF3D71; }
.summary-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

/* Info Row */
.info-row { display: flex; gap: 16px; }
.section-title { color: var(--text-primary); font-size: 14px; margin: 0 0 14px; }

.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.link { color: var(--accent-start); cursor: pointer; }
.info-value.link:hover { text-decoration: underline; }

/* Metric Bars */
.metric-bars { display: flex; flex-direction: column; gap: 10px; }
.metric-bar-row { display: flex; align-items: center; gap: 10px; }
.metric-name { width: 110px; font-size: 12px; color: var(--text-secondary); text-transform: capitalize; flex-shrink: 0; }
.metric-bar-wrap { flex: 1; height: 8px; background: var(--border-color); border-radius: 4px; overflow: hidden; }
.metric-bar { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.metric-bar.bar-success { background: linear-gradient(90deg, var(--accent-start), #00D68F); }
.metric-bar.bar-warning { background: linear-gradient(90deg, var(--accent-start), #FFAA00); }
.metric-bar.bar-danger { background: linear-gradient(90deg, var(--accent-start), #FF3D71); }
.metric-score { width: 40px; font-size: 12px; color: var(--text-primary); font-weight: 600; text-align: right; flex-shrink: 0; }

/* Results Table */
.results-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 10px;
}
.toolbar-right { display: flex; gap: 8px; }
.count-badge {
  display: inline-flex;
  align-items: center;
  background: rgba(108, 92, 231, 0.15);
  color: var(--accent-start);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
}

.result-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
}

.sample-id { font-family: monospace; font-size: 12px; color: var(--accent-start); }
.text-muted { color: var(--text-secondary); font-size: 12px; }
.text-success { color: #00D68F; font-weight: 600; }
.text-warning { color: #FFAA00; font-weight: 600; }
.text-danger { color: #FF3D71; font-weight: 600; }

.score-cell { display: flex; align-items: center; gap: 6px; }
.score-dot { width: 8px; height: 8px; border-radius: 50%; }
.score-dot.bar-success { background: #00D68F; }
.score-dot.bar-warning { background: #FFAA00; }
.score-dot.bar-danger { background: #FF3D71; }

/* Mini bars */
.mini-bars { display: flex; gap: 3px; align-items: center; }
.mini-bar-item { width: 28px; height: 6px; background: var(--border-color); border-radius: 3px; overflow: hidden; }
.mini-bar { height: 100%; border-radius: 3px; }
.mini-bar.bar-success { background: #00D68F; }
.mini-bar.bar-warning { background: #FFAA00; }
.mini-bar.bar-danger { background: #FF3D71; }

/* Expand */
.expand-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px;
}
.expand-section { display: flex; flex-direction: column; gap: 6px; }
.expand-section--full { width: 100%; }
.expand-section h5 { font-size: 11px; color: var(--text-secondary); margin: 0; text-transform: uppercase; letter-spacing: 0.5px; }

.json-block {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow: auto;
  margin: 0;
  line-height: 1.6;
}

/* JSON syntax highlighting */
.json-input { background: var(--code-bg, var(--bg-card)); }
.json-key { color: #6C5CE7; font-weight: 600; }
.json-str { color: #00B894; }
.json-num { color: #E17055; }
.json-bool { color: #0984E3; }

/* Output blocks */
.json-output { font-family: inherit; white-space: pre-wrap; word-break: break-word; }
.output-match { border-color: rgba(0, 214, 143, 0.3); }
.output-diff { border-color: rgba(255, 170, 0, 0.4); }

.error-block { border-color: rgba(255, 61, 113, 0.3); color: #FF3D71; }

.metric-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.metric-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
}
.metric-chip.pass { border-color: rgba(0, 214, 143, 0.3); }
.metric-chip.fail { border-color: rgba(255, 61, 113, 0.3); }
.chip-name { color: var(--text-secondary); min-width: 80px; }
.chip-score { color: var(--text-primary); font-weight: 600; }
.chip-reason { color: var(--text-muted); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  border-top: 1px solid var(--border-color);
}
</style>
