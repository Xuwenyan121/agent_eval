<template>
  <div class="reports-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input v-model="search" placeholder="搜索报告..." prefix-icon="Search" clearable style="width: 240px" @input="onSearch" />
        <el-select v-model="sortBy" style="width: 160px">
          <el-option label="最新优先" value="-created_at" />
          <el-option label="最高分优先" value="-score" />
          <el-option label="Bad Case 最多" value="-badcase" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="loadReports">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Report Cards Grid -->
    <div v-loading="store.loading" class="reports-grid">
      <div
        v-for="task in sortedReports"
        :key="task.id"
        class="card report-card"
        @click="$router.push(`/reports/${task.id}`)"
      >
        <div class="report-header">
          <h4 class="report-name">{{ task.name }}</h4>
          <StatusBadge :status="task.status" />
        </div>

        <div class="report-meta">
          <span class="meta-item">
            <el-icon><Monitor /></el-icon>
            {{ task.agent_name || '未知' }}
          </span>
          <span class="meta-item">
            <el-icon><FolderOpened /></el-icon>
            {{ task.dataset_name || '未知' }}
          </span>
        </div>

        <div class="report-scores">
          <div class="score-main">
            <ScoreRing :score="task.average_score ?? 0" :size="56" />
            <div class="score-detail">
              <span class="score-label">综合得分</span>
              <span class="score-value" :class="scoreClass(task.average_score)">
                {{ task.average_score != null ? (task.average_score * 100).toFixed(0) + '%' : '—' }}
              </span>
            </div>
          </div>
        </div>

        <div class="report-stats">
          <div class="stat-item">
            <span class="stat-num">{{ task.result_count ?? 0 }}</span>
            <span class="stat-label">结果数</span>
          </div>
          <div class="stat-item">
            <span class="stat-num" :class="(task.badcase_count ?? 0) > 0 ? 'danger' : ''">
              {{ task.badcase_count ?? 0 }}
            </span>
            <span class="stat-label">Bad Case</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ task.average_score != null ? ((task.average_score >= 0.8 ? task.average_score : 0) * 100).toFixed(0) + '%' : '—' }}</span>
            <span class="stat-label">通过率</span>
          </div>
        </div>

        <div class="report-footer">
          <span class="text-muted">{{ formatDate(task.completed_at || task.created_at) }}</span>
          <el-button text size="small" style="color: #6C5CE7">
            查看报告
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <EmptyState
      v-if="!store.loading && sortedReports.length === 0"
      icon="DataAnalysis"
      title="暂无报告"
      description="评测任务完成后会自动生成报告。创建并运行任务以查看结果。"
      action-label="新建任务"
      @action="$router.push('/tasks/create')"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { formatDate, debounce } from '@/utils'
import { StatusBadge, EmptyState, ScoreRing } from '@/components'

const store = useTaskStore()
const search = ref('')
const sortBy = ref('-created_at')

const completedTasks = computed(() =>
  store.tasks.filter(t => t.status === 'completed')
)

const sortedReports = computed(() => {
  let list = [...completedTasks.value]

  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(t =>
      t.name?.toLowerCase().includes(q) ||
      t.agent_name?.toLowerCase().includes(q) ||
      t.dataset_name?.toLowerCase().includes(q)
    )
  }

  switch (sortBy.value) {
    case '-score':
      list.sort((a, b) => (b.average_score ?? 0) - (a.average_score ?? 0))
      break
    case '-badcase':
      list.sort((a, b) => (b.badcase_count ?? 0) - (a.badcase_count ?? 0))
      break
    default:
      // -created_at is already the default order from API
      break
  }

  return list
})

const onSearch = debounce(() => {}, 300)

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'danger'
}

async function loadReports() {
  await store.fetchTasks({ status: 'completed', page_size: 50, ordering: '-completed_at' })
}

onMounted(() => loadReports())
</script>

<style scoped>
.reports-page { display: flex; flex-direction: column; gap: 16px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left { display: flex; gap: 10px; align-items: center; }

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.report-card {
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.report-card:hover {
  border-color: rgba(108, 92, 231, 0.4);
  transform: translateY(-2px);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.report-name { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0; }

.report-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}
.meta-item { display: flex; align-items: center; gap: 4px; }

.report-scores { display: flex; align-items: center; gap: 16px; }
.score-main { display: flex; align-items: center; gap: 14px; }
.score-detail { display: flex; flex-direction: column; gap: 2px; }
.score-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; }
.score-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.score-value.success { color: #00D68F; }
.score-value.warning { color: #FFAA00; }
.score-value.danger { color: #FF3D71; }

.report-stats {
  display: flex;
  gap: 20px;
  padding: 12px 0;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-num { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.stat-num.danger { color: #FF3D71; }
.stat-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

.report-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-muted { color: var(--text-secondary); font-size: 12px; }
</style>
