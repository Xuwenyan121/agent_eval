<template>
  <div class="dashboard" v-loading="loading">
    <!-- Stat Cards Row -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <StatCardMini
          :value="stats.taskCount"
          label="总评测数"
          icon="DataAnalysis"
          icon-color="#6C5CE7"
        />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCardMini
          :value="avgScoreDisplay"
          label="平均得分"
          icon="TrendCharts"
          icon-color="#00D68F"
          :decimals="3"
        />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCardMini
          :value="stats.activeAgentCount"
          :label="`活跃智能体 (${stats.agentCount} 个)`"
          icon="Monitor"
          icon-color="#FF6B9D"
        />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCardMini
          :value="stats.badcaseCount"
          label="待处理 BadCase"
          icon="WarningFilled"
          icon-color="#FFAA00"
        />
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :sm="16">
        <div class="card">
          <TrendChart
            title="评测趋势 (近7天)"
            :labels="stats.trendLabels"
            :data="stats.trendCounts"
            :height="260"
          />
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="card">
          <StatusPieChart
            title="任务状态分布"
            :data="stats.statusDistribution"
            :height="260"
          />
        </div>
      </el-col>
    </el-row>

    <!-- Bottom Row -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :sm="8">
        <div class="card">
          <ScoreDistChart
            title="分数分布"
            :labels="Object.keys(stats.scoreDistribution)"
            :data="Object.values(stats.scoreDistribution)"
            :height="260"
          />
        </div>
      </el-col>
      <el-col :xs="24" :sm="16">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">最近任务</h3>
            <el-button text type="primary" @click="$router.push('/tasks')" class="view-all-btn">
              查看全部
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
          <div v-if="stats.recentTasks.length === 0" class="empty-recent">
            <el-icon :size="32" color="var(--border-color)"><Document /></el-icon>
            <p>暂无评测任务</p>
            <el-button class="btn-gradient" size="small" @click="$router.push('/tasks/create')">
              创建首个任务
            </el-button>
          </div>
          <el-table
            v-else
            :data="stats.recentTasks"
            :show-header="true"
            size="small"
            stripe
            :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
            @row-click="(row) => $router.push(`/tasks/${row.id}`)"
            class="task-table"
          >
            <el-table-column prop="name" label="任务名称" min-width="160">
              <template #default="{ row }">
                <span class="task-name">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <StatusBadge :status="row.status" />
              </template>
            </el-table-column>
            <el-table-column label="得分" width="90" align="center">
              <template #default="{ row }">
                <span class="score-value" :style="{ color: scoreColor(row.overall_score) }">
                  {{ row.overall_score != null ? row.overall_score.toFixed(3) : '—' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="样本数" width="80" align="center">
              <template #default="{ row }">
                <span class="text-secondary">{{ row.total_samples || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">
                <span class="text-secondary">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <!-- Quick Links Row -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="12" :sm="6" v-for="link in quickLinks" :key="link.path">
        <div class="quick-link" @click="$router.push(link.path)">
          <el-icon :size="20" :color="link.color">
            <component :is="link.icon" />
          </el-icon>
          <span>{{ link.label }}</span>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { dashboardApi } from '@/api'
import { formatDate, scoreColor } from '@/utils'
import { StatCardMini, StatusBadge } from '@/components'
import { TrendChart, ScoreDistChart, StatusPieChart } from '@/components/charts'

const loading = ref(true)
const stats = ref({
  agentCount: 0,
  activeAgentCount: 0,
  datasetCount: 0,
  taskCount: 0,
  badcaseCount: 0,
  metricCount: 0,
  avgScore: null,
  completedCount: 0,
  runningCount: 0,
  statusDistribution: { pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0 },
  scoreDistribution: { '0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0, '0.6-0.8': 0, '0.8-1.0': 0 },
  trendLabels: [],
  trendCounts: [],
  recentTasks: [],
  agents: [],
})

const avgScoreDisplay = computed(() => {
  return stats.value.avgScore != null ? stats.value.avgScore.toFixed(3) : '—'
})

const quickLinks = [
  { path: '/agents/create', label: '新建智能体', icon: 'Plus', color: '#6C5CE7' },
  { path: '/datasets', label: '管理数据集', icon: 'FolderOpened', color: '#00D68F' },
  { path: '/tasks/create', label: '运行评测', icon: 'VideoPlay', color: '#FF6B9D' },
  { path: '/reports', label: '查看报告', icon: 'TrendCharts', color: '#FFAA00' },
]

onMounted(async () => {
  try {
    stats.value = await dashboardApi.getStats()
  } catch (e) {
    console.error('Dashboard load error:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  min-height: 100%;
}

.stat-row .el-col {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.view-all-btn {
  font-size: 12px;
  color: #6C5CE7 !important;
}

.task-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.08);
  --el-table-border-color: var(--border-color);
  cursor: pointer;
}

.task-name {
  font-weight: 500;
  color: var(--text-primary);
}

.score-value {
  font-weight: 700;
  font-size: 13px;
}

.text-secondary {
  color: var(--text-secondary);
  font-size: 12px;
}

.empty-recent {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 0;
  gap: 8px;
}
.empty-recent p {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0;
}

.quick-link {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}
.quick-link:hover {
  border-color: #6C5CE7;
  transform: translateY(-1px);
}
</style>
