<template>
  <div class="badcases-page">
    <div class="page-toolbar">
      <h3 style="margin: 0; color: var(--text-primary)">BadCase 管理</h3>
      <div class="toolbar-right">
        <el-select v-model="filterTaskId" placeholder="选择任务" size="small" clearable filterable style="width: 220px" @change="loadBadcases">
          <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-select v-model="filterStatus" size="small" style="width: 130px" clearable @change="currentPage = 1; loadBadcases()">
          <el-option label="全部状态" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="审核中" value="reviewing" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已驳回" value="dismissed" />
        </el-select>
        <el-button size="small" type="primary" @click="loadBadcases">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>
    </div>

    <!-- BadCase Table -->
    <div class="card" style="padding: 0; overflow: hidden">
      <el-table
        :data="badcases"
        v-loading="loading"
        class="bc-table"
        :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
        row-key="id"
        empty-text=""
        @row-click="openDetail"
      >
        <el-table-column prop="id" label="ID" width="100">
          <template #default="{ row }">
            <span class="mono-text">{{ row.id?.slice(0, 8) }}...</span>
          </template>
        </el-table-column>
        <el-table-column label="样本 ID" width="160">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              class="sample-link"
              @click.stop="$router.push(`/datasets/${row.dataset}`)"
            >
              {{ row.result_detail?.sample_id || '—' }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="综合分" width="90" align="center">
          <template #default="{ row }">
            <span class="score-text" :class="scoreClass(row.result_detail?.overall_score)">
              {{ formatScore(row.result_detail?.overall_score) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="命中规则" min-width="140">
          <template #default="{ row }">
            <div v-if="row.matched_rules?.length" class="rule-tags">
              <el-tag v-for="mr in row.matched_rules" :key="mr.rule_id" size="small" effect="plain" type="warning">
                {{ mr.rule_name }}
              </el-tag>
            </div>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="输入预览" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-muted">{{ row.result_detail?.input?.slice(0, 80) || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <StatusBadge :status="row.status" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="140">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState v-if="!loading && badcases.length === 0" icon="WarningFilled" title="暂无 BadCase" description="选择已完成的任务查看 BadCase 列表" />

      <div class="pagination-wrap" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          background
          @current-change="loadBadcases"
        />
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      title="BadCase 详情"
      size="600px"
      destroy-on-close
    >
      <template v-if="detail">
        <div class="detail-section">
          <h5>综合评分</h5>
          <div class="detail-score-row">
            <span class="detail-score" :class="scoreClass(detail.result_detail?.overall_score)">
              {{ formatScore(detail.result_detail?.overall_score) }}
            </span>
            <StatusBadge :status="detail.status" />
          </div>
        </div>

        <div class="detail-section" v-if="detail.matched_rules?.length">
          <h5>命中规则</h5>
          <div class="rule-tags">
            <el-tag v-for="mr in detail.matched_rules" :key="mr.rule_id" type="warning" effect="plain">
              {{ mr.rule_name }}
            </el-tag>
          </div>
          <div v-for="mr in detail.matched_rules" :key="mr.rule_id" class="rule-reason">
            {{ mr.reason }}
          </div>
        </div>

        <div class="detail-section">
          <h5>输入</h5>
          <pre class="json-block">{{ detail.result_detail?.input || '—' }}</pre>
        </div>
        <div class="detail-section">
          <h5>期望输出</h5>
          <pre class="json-block">{{ formatOutput(detail.result_detail?.expected_output) }}</pre>
        </div>
        <div class="detail-section">
          <h5>实际输出</h5>
          <pre class="json-block bc-actual">{{ formatOutput(detail.result_detail?.actual_output) }}</pre>
        </div>

        <div class="detail-section" v-if="detail.result_detail?.metric_results">
          <h5>指标评分</h5>
          <div class="metric-chips">
            <div v-for="(val, key) in detail.result_detail.metric_results" :key="key" class="metric-chip" :class="val.passed ? 'pass' : 'fail'">
              <span class="chip-name">{{ key }}</span>
              <span class="chip-score">{{ ((val.score || 0) * 100).toFixed(0) }}%</span>
              <span class="chip-reason" v-if="val.reason">{{ val.reason }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detail.trace">
          <h5>执行链路</h5>
          <div class="trace-info">
            <span>Trace ID: {{ detail.trace.trace_id?.slice(0, 16) }}...</span>
            <span>耗时: {{ detail.trace.total_duration_ms }}ms</span>
            <span>Tokens: {{ detail.trace.total_tokens }}</span>
          </div>
          <pre class="json-block" style="max-height: 200px">{{ formatJson(detail.trace.spans) }}</pre>
        </div>

        <div class="detail-section" v-if="detail.review_comment">
          <h5>审核备注</h5>
          <p class="text-muted">{{ detail.review_comment }}</p>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { taskApi } from '@/api'
import { formatDate } from '@/utils'
import { StatusBadge, EmptyState } from '@/components'
import { ElMessage } from 'element-plus'

const router = useRouter()
const tasks = ref([])
const badcases = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const detail = ref(null)
const filterTaskId = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

async function loadTasks() {
  try {
    const res = await taskApi.list({ status: 'completed', page_size: 100 })
    tasks.value = res.results || []
  } catch { /* ignore */ }
}

async function loadBadcases() {
  if (!filterTaskId.value) {
    badcases.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    const res = await taskApi.listBadcases(filterTaskId.value, params)
    badcases.value = res.results || []
    total.value = res.count || 0
  } catch {
    ElMessage.error('加载 BadCase 失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  try {
    detail.value = await taskApi.getBadcaseDetail(filterTaskId.value, row.id)
    drawerVisible.value = true
  } catch {
    ElMessage.error('加载详情失败')
  }
}

function formatScore(val) {
  if (val == null) return '—'
  return (val * 100).toFixed(0) + '%'
}

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 0.8) return 'text-success'
  if (score >= 0.5) return 'text-warning'
  return 'text-danger'
}

function formatOutput(val) {
  if (!val) return '—'
  try {
    const parsed = typeof val === 'string' ? JSON.parse(val) : val
    if (typeof parsed === 'object' && parsed !== null) {
      const text = parsed.expected_output || parsed.output || parsed.answer || parsed.text
      if (text) return String(text)
      return JSON.stringify(parsed, null, 2)
    }
    return String(parsed)
  } catch {
    return String(val)
  }
}

function formatJson(val) {
  if (!val) return '—'
  try {
    return JSON.stringify(val, null, 2)
  } catch {
    return String(val)
  }
}

onMounted(async () => {
  await loadTasks()
})
</script>

<style scoped>
.badcases-page { display: flex; flex-direction: column; gap: 16px; }

.page-toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }

.bc-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: var(--border-color);
}
.bc-table :deep(.el-table__row) { cursor: pointer; }
.bc-table :deep(.el-table__row:hover) { background: var(--row-hover-bg); }

.mono-text { font-family: monospace; font-size: 11px; color: var(--text-secondary); }
.text-muted { color: var(--text-secondary); font-size: 12px; }
.score-text { font-weight: 700; font-size: 14px; }
.text-success { color: #00D68F; }
.text-warning { color: #FFAA00; }
.text-danger { color: #FF3D71; }

.sample-link { font-family: monospace; font-size: 12px; padding: 0; }

.rule-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.rule-reason { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

.pagination-wrap { display: flex; justify-content: center; padding: 16px; }

.detail-section { margin-bottom: 20px; }
.detail-section h5 { color: var(--text-primary); font-size: 13px; margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.detail-score-row { display: flex; align-items: center; gap: 12px; }
.detail-score { font-size: 28px; font-weight: 700; }

.json-block {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  font-family: monospace;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}
.bc-actual { border-color: #FF3D71; }

.metric-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.metric-chip {
  display: flex; flex-direction: column; gap: 2px;
  padding: 6px 10px; border-radius: 8px;
  background: var(--bg-card); border: 1px solid var(--border-color);
  min-width: 90px;
}
.metric-chip.pass { border-color: #00D68F; }
.metric-chip.fail { border-color: #FF3D71; }
.chip-name { font-size: 11px; color: var(--text-secondary); }
.chip-score { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.chip-reason { font-size: 10px; color: var(--text-muted); line-height: 1.3; }

.trace-info { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
</style>