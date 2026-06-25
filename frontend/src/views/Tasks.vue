<template>
  <div class="tasks-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input v-model="search" placeholder="搜索评测任务..." prefix-icon="Search" clearable style="width: 240px" @input="onSearch" />
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 140px" @change="loadTasks">
          <el-option label="等待中" value="pending" />
          <el-option label="运行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button class="btn-gradient" @click="$router.push('/tasks/create')">
          <el-icon><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row" v-if="store.total > 0">
      <div class="stat-chip">
        <span class="stat-num accent">{{ store.total }}</span>
        <span class="stat-label">总计</span>
      </div>
      <div class="stat-chip">
        <span class="stat-num warning">{{ store.runningCount }}</span>
        <span class="stat-label">运行中</span>
      </div>
      <div class="stat-chip">
        <span class="stat-num success">{{ store.completedCount }}</span>
        <span class="stat-label">已完成</span>
      </div>
    </div>

    <!-- Table -->
    <div class="card" style="padding: 0; overflow: hidden">
      <el-table
        :data="filteredTasks"
        v-loading="store.loading"
        @row-click="(row) => $router.push(`/tasks/${row.id}`)"
        class="task-table"
        :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
        empty-text=""
      >
        <el-table-column prop="name" label="任务" min-width="180">
          <template #default="{ row }">
            <div class="task-name">
              <span class="name-text">{{ row.name }}</span>
              <div class="task-meta">
                <span class="meta-item"><el-icon><Monitor /></el-icon> {{ row.agent_name || '—' }}</span>
                <span class="meta-item"><el-icon><FolderOpened /></el-icon> {{ row.dataset_name || '—' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="结果数" width="90" align="center">
          <template #default="{ row }">
            <span class="result-count">{{ row.result_count ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="平均分" width="100" align="center">
          <template #default="{ row }">
            <div class="score-cell" v-if="row.average_score != null">
              <ScoreRing :score="row.average_score" :size="32" />
            </div>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="Bad Case" width="90" align="center">
          <template #default="{ row }">
            <span :class="row.badcase_count > 0 ? 'badcase-count' : 'text-muted'">
              {{ row.badcase_count ?? '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">
            <span class="text-muted" v-if="row.started_at && row.completed_at">
              {{ formatDuration(row.started_at, row.completed_at) }}
            </span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button
                v-if="row.status === 'pending' || row.status === 'failed'"
                size="small" text type="success"
                @click.stop="handleRun(row)"
                :loading="runningId === row.id"
              >
                <el-icon><VideoPlay /></el-icon>
              </el-button>
              <el-button
                v-if="row.status === 'running'"
                size="small" text type="warning"
                @click.stop="handleStop(row)"
              >
                <el-icon><VideoPause /></el-icon>
              </el-button>
              <el-button size="small" text @click.stop="$router.push(`/tasks/${row.id}`)">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click.stop="confirmDelete(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState
        v-if="!store.loading && filteredTasks.length === 0"
        icon="SetUp"
        title="暂无评测任务"
        description="创建评测任务以测试智能体在数据集上的表现。"
        action-label="新建任务"
        @action="$router.push('/tasks/create')"
      />
    </div>

    <!-- Delete Confirm -->
    <ConfirmDialog
      v-model:visible="showDeleteDialog"
      title="删除任务"
      :message="`确定删除任务 '${deleteTarget?.name}' 吗？`"
      detail="这将同时删除所有关联的评测结果。"
      confirm-label="删除"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { formatDate, debounce } from '@/utils'
import { StatusBadge, EmptyState, ConfirmDialog, ScoreRing } from '@/components'
import { ElMessage } from 'element-plus'

const store = useTaskStore()
const search = ref('')
const filterStatus = ref('')
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)
const runningId = ref(null)

const filteredTasks = computed(() => {
  let list = store.tasks
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(t =>
      t.name?.toLowerCase().includes(q) ||
      t.agent_name?.toLowerCase().includes(q) ||
      t.dataset_name?.toLowerCase().includes(q)
    )
  }
  return list
})

const onSearch = debounce(() => {}, 300)

function formatDuration(start, end) {
  const ms = new Date(end) - new Date(start)
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${Math.round(ms / 1000)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}

async function loadTasks() {
  const params = {}
  if (filterStatus.value) params.status = filterStatus.value
  await store.fetchTasks(params)
}

async function handleRun(task) {
  runningId.value = task.id
  try {
    await store.runTask(task.id)
    ElMessage.success('任务已启动')
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '启动任务失败')
  } finally {
    runningId.value = null
  }
}

async function handleStop(task) {
  try {
    await store.stopTask(task.id)
    ElMessage.success('任务已停止')
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '停止任务失败')
  }
}

function confirmDelete(task) {
  deleteTarget.value = task
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await store.deleteTask(deleteTarget.value.id)
    showDeleteDialog.value = false
    deleteTarget.value = null
    ElMessage.success('任务已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '删除任务失败')
  }
}

onMounted(() => loadTasks())
</script>

<style scoped>
.tasks-page { display: flex; flex-direction: column; gap: 16px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left { display: flex; gap: 10px; align-items: center; }

.stats-row {
  display: flex;
  gap: 12px;
}
.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 14px;
}
.stat-num { font-size: 18px; font-weight: 700; }
.stat-num.accent { color: #6C5CE7; }
.stat-num.warning { color: #FFAA00; }
.stat-num.success { color: #00D68F; }
.stat-label { font-size: 12px; color: var(--text-secondary); }

.task-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
  cursor: pointer;
}

.task-name { display: flex; flex-direction: column; gap: 4px; }
.name-text { font-weight: 500; color: var(--text-primary); font-size: 13px; }
.task-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-secondary); }
.meta-item { display: flex; align-items: center; gap: 3px; }

.result-count { color: var(--text-primary); font-weight: 600; }
.score-cell { display: flex; justify-content: center; }
.badcase-count { color: #FF3D71; font-weight: 600; }
.text-muted { color: var(--text-secondary); font-size: 12px; }

.action-group { display: flex; gap: 2px; }
.action-group .el-button { color: var(--text-secondary); font-size: 14px; }
.action-group .el-button:hover { color: #6C5CE7; }
.action-group .el-button[type="danger"]:hover { color: #FF3D71; }
.action-group .el-button[type="success"]:hover { color: #00D68F; }
.action-group .el-button[type="warning"]:hover { color: #FFAA00; }
</style>
