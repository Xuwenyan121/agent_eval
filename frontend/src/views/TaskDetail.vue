<template>
  <div class="task-detail-page">
    <!-- Header -->
    <div class="page-header">
      <el-button text @click="$router.push('/tasks')" style="color: var(--text-secondary)">
        <el-icon><ArrowLeft /></el-icon>
        返回任务列表
      </el-button>
      <div class="header-actions" v-if="task">
        <el-button
          v-if="task.status === 'pending' || task.status === 'failed'"
          class="btn-gradient"
          @click="handleRun"
          :loading="running"
        >
          <el-icon><VideoPlay /></el-icon>
          运行任务
        </el-button>
        <el-button v-if="task.status === 'running'" type="warning" plain @click="handleStop">
          <el-icon><VideoPause /></el-icon>
          停止任务
        </el-button>
        <el-button @click="$router.push(`/reports/${task.id}`)" v-if="task.status === 'completed'">
          <el-icon><DataAnalysis /></el-icon>
          查看报告
        </el-button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else-if="task">
      <!-- Progress Tracker (if running) -->
      <ProgressTracker
        v-if="task.status === 'running' && progress"
        :phase="progress.progress?.phase"
        :progress="progress.progress?.progress"
        :collect-done="progress.progress?.collect_progress?.completed || 0"
        :collect-total="progress.progress?.collect_progress?.total || 0"
        :collect-failed="progress.progress?.collect_progress?.failed || 0"
        :eval-done="progress.progress?.eval_progress?.completed || 0"
        :eval-total="progress.progress?.eval_progress?.total || 0"
      />

      <!-- Info Card -->
      <div class="card info-card">
        <div class="info-header">
          <div>
            <h3 class="task-name">{{ task.name }}</h3>
          </div>
          <StatusBadge :status="task.status" size="large" />
        </div>

        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">智能体</span>
            <span class="info-value link" @click="$router.push(`/agents/${task.agent}/edit`)">
              {{ task.agent_name || '—' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">数据集</span>
            <span class="info-value link" @click="$router.push(`/datasets/${task.dataset}`)">
              {{ task.dataset_name || '—' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">裁判模型</span>
            <span class="info-value">{{ task.judge_model?.model || '无' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">并发数</span>
            <span class="info-value">{{ task.parallel }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">样本限制</span>
            <span class="info-value">{{ task.limit || '全部' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">开始时间</span>
            <span class="info-value">{{ task.started_at ? formatDate(task.started_at) : '—' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">完成时间</span>
            <span class="info-value">{{ task.completed_at ? formatDate(task.completed_at) : '—' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">耗时</span>
            <span class="info-value">{{ duration }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDate(task.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Results Summary -->
      <div class="card" v-if="task.status === 'completed' && task.summary">
        <h4 class="section-title">结果概览</h4>
        <div class="results-grid">
          <div class="result-box">
            <span class="result-num accent">{{ task.summary.total_results || task.result_count || 0 }}</span>
            <span class="result-label">总结果数</span>
          </div>
          <div class="result-box">
            <span class="result-num" :class="scoreClass">{{ formatScore(task.summary.average_score ?? task.average_score) }}</span>
            <span class="result-label">平均分</span>
          </div>
          <div class="result-box">
            <span class="result-num" :class="(task.summary.badcase_count ?? task.badcase_count) > 0 ? 'danger' : ''">
              {{ task.summary.badcase_count ?? task.badcase_count ?? 0 }}
            </span>
            <span class="result-label">Bad Case 数</span>
          </div>
          <div class="result-box" v-if="task.summary.pass_rate != null">
            <span class="result-num success">{{ (task.summary.pass_rate * 100).toFixed(0) }}%</span>
            <span class="result-label">通过率</span>
          </div>
        </div>

        <!-- Metric Breakdown -->
        <div class="metric-breakdown" v-if="task.summary.metric_averages">
          <h5 style="color: var(--text-secondary); font-size: 12px; margin: 16px 0 8px; text-transform: uppercase;">指标平均分</h5>
          <div class="metric-bars">
            <div v-for="(score, name) in task.summary.metric_averages" :key="name" class="metric-bar-row">
              <span class="metric-name">{{ name }}</span>
              <div class="metric-bar-wrap">
                <div class="metric-bar" :style="{ width: (score * 100) + '%' }" :class="barClass(score)"></div>
              </div>
              <span class="metric-score">{{ (score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Evaluator Config -->
      <div class="card" v-if="task.evaluator_config?.metrics?.length">
        <h4 class="section-title">评估器配置</h4>
        <el-table
          :data="task.evaluator_config.metrics"
          class="config-table"
          :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
          size="small"
        >
          <el-table-column prop="type" label="指标" min-width="120">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="weight" label="权重" width="100" align="center">
            <template #default="{ row }">
              <span class="accent-text">{{ row.weight }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="threshold" label="阈值" width="100" align="center">
            <template #default="{ row }">
              {{ row.threshold ?? '—' }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- MLflow Info -->
      <div class="card" v-if="task.mlflow_run_id">
        <h4 class="section-title">MLflow 追踪</h4>
        <div class="info-item">
          <span class="info-label">运行 ID</span>
          <span class="info-value mono">{{ task.mlflow_run_id }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'
import { formatDate } from '@/utils'
import { StatusBadge, ProgressTracker } from '@/components'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const store = useTaskStore()

const taskId = route.params.id
const loading = ref(true)
const running = ref(false)
let progressInterval = null

const task = computed(() => store.currentTask)
const progress = computed(() => store.taskProgress[taskId])

const duration = computed(() => {
  if (!task.value?.started_at || !task.value?.completed_at) return '—'
  const ms = new Date(task.value.completed_at) - new Date(task.value.started_at)
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${Math.round(ms / 1000)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
})

const scoreClass = computed(() => {
  const score = task.value?.summary?.average_score ?? task.value?.average_score
  if (score == null) return ''
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
})

function formatScore(val) {
  if (val == null) return '—'
  return (val * 100).toFixed(0) + '%'
}

function barClass(score) {
  if (score >= 0.8) return 'bar-success'
  if (score >= 0.5) return 'bar-warning'
  return 'bar-danger'
}

async function loadTask() {
  loading.value = true
  try {
    await store.fetchTask(taskId)
  } catch {
    ElMessage.error('加载任务失败')
    router.push('/tasks')
  } finally {
    loading.value = false
  }
}

function startProgressPolling() {
  store.fetchProgress(taskId)
  progressInterval = setInterval(() => {
    if (task.value?.status === 'running') {
      store.fetchProgress(taskId)
    }
  }, 3000)
}

function stopProgressPolling() {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }
}

async function handleRun() {
  running.value = true
  try {
    await store.runTask(taskId)
    ElMessage.success('任务已启动')
    // 立即开始轮询进度，不再调用 loadTask() 避免后端返回旧状态覆盖本地 running 状态
    startProgressPolling()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '启动任务失败')
  } finally {
    running.value = false
  }
}

async function handleStop() {
  try {
    await store.stopTask(taskId)
    ElMessage.success('任务已停止')
    stopProgressPolling()
    await loadTask()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '停止任务失败')
  }
}

onMounted(async () => {
  await loadTask()
  if (task.value?.status === 'running') {
    startProgressPolling()
  }
})

onUnmounted(() => stopProgressPolling())
</script>

<style scoped>
.task-detail-page { display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; justify-content: space-between; align-items: center; }
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
.task-name { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.link { color: var(--accent-start); cursor: pointer; }
.info-value.link:hover { text-decoration: underline; }
.info-value.mono { font-family: monospace; font-size: 12px; }

.section-title { color: var(--text-primary); font-size: 15px; margin: 0 0 16px; }

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
}
.result-box {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.result-num { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.result-num.accent { color: var(--accent-start); }
.result-num.success { color: #00D68F; }
.result-num.warning { color: #FFAA00; }
.result-num.danger { color: #FF3D71; }
.result-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; }

.metric-breakdown { margin-top: 8px; }
.metric-bars { display: flex; flex-direction: column; gap: 8px; }
.metric-bar-row { display: flex; align-items: center; gap: 12px; }
.metric-name { width: 120px; font-size: 12px; color: var(--text-secondary); text-transform: capitalize; }
.metric-bar-wrap { flex: 1; height: 8px; background: var(--border-color); border-radius: 4px; overflow: hidden; }
.metric-bar { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.metric-bar.bar-success { background: #00D68F; }
.metric-bar.bar-warning { background: #FFAA00; }
.metric-bar.bar-danger { background: #FF3D71; }
.metric-score { width: 40px; font-size: 12px; color: var(--text-primary); font-weight: 600; text-align: right; }

.config-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: var(--border-color);
}
.accent-text { color: var(--accent-start); font-weight: 600; }
</style>
