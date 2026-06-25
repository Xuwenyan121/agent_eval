<template>
  <div class="agents-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="search"
          placeholder="搜索智能体..."
          prefix-icon="Search"
          clearable
          style="width: 260px"
          @input="onSearch"
        />
        <el-select v-model="filterProtocol" placeholder="协议类型" clearable style="width: 160px" @change="loadAgents">
          <el-option label="HTTP SSE" value="http_sse" />
          <el-option label="HTTP JSON" value="http_json" />
          <el-option label="OpenAI Compat" value="openai_compat" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 130px" @change="loadAgents">
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button class="btn-gradient" @click="$router.push('/agents/create')">
          <el-icon><Plus /></el-icon>
          新建智能体
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="card" style="padding: 0; overflow: hidden">
      <el-table
        :data="filteredAgents"
        v-loading="store.loading"
        @row-click="(row) => $router.push(`/agents/${row.id}/edit`)"
        class="agent-table"
        :header-cell-style="{ background: 'var(--table-header-bg)', color: 'var(--text-secondary)', fontSize: '12px' }"
        empty-text=""
      >
        <el-table-column prop="name" label="智能体名称" min-width="180">
          <template #default="{ row }">
            <div class="agent-name">
              <span class="name-text">{{ row.name }}</span>
              <span class="name-url">{{ row.endpoint_url }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="protocol" label="协议" width="140">
          <template #default="{ row }">
            <el-tag :type="protocolTagType(row.protocol)" size="small" effect="dark" round>
              {{ protocolLabel(row.protocol) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="任务数" width="80" align="center">
          <template #default="{ row }">
            <span class="text-muted">{{ row.task_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group class="action-group">
              <el-button size="small" text @click.stop="$router.push(`/agents/${row.id}/edit`)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" text @click.stop="handleTest(row)" :loading="testingId === row.id">
                <el-icon><Connection /></el-icon>
              </el-button>
              <el-button size="small" text type="danger" @click.stop="confirmDelete(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <EmptyState
        v-if="!store.loading && filteredAgents.length === 0"
        icon="Monitor"
        title="暂无智能体"
        description="添加你的第一个智能体端点，开始运行评测。"
        action-label="添加智能体"
        @action="$router.push('/agents/create')"
      />
    </div>

    <!-- Test Result Dialog -->
    <el-dialog v-model="showTestDialog" title="连接测试结果" width="520px" class="test-dialog">
      <div v-if="testResult" class="test-body">
        <div class="test-status" :class="testResult.status">
          <el-icon :size="24">
            <component :is="testResult.status === 'online' ? 'CircleCheckFilled' : 'CircleCloseFilled'" />
          </el-icon>
          <span>{{ testResult.status === 'online' ? '连接成功' : '连接失败' }}</span>
        </div>
        <el-descriptions :column="2" border size="small" class="test-details">
          <el-descriptions-item label="延迟">{{ testResult.latency_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="协议验证">
            <el-tag :type="testResult.protocol_verified ? 'success' : 'danger'" size="small">
              {{ testResult.protocol_verified ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据块数" v-if="testResult.sse_chunks_received">
            {{ testResult.sse_chunks_received }}
          </el-descriptions-item>
          <el-descriptions-item label="错误信息" v-if="testResult.error">
            <span style="color: #FF3D71">{{ testResult.error }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="testResult.sample_output" class="test-output">
          <div class="output-label">示例输出</div>
          <pre class="output-text">{{ truncate(testResult.sample_output, 300) }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- Delete Confirm -->
    <ConfirmDialog
      v-model:visible="showDeleteDialog"
      title="删除智能体"
      :message="`确认删除智能体 '${deleteTarget?.name}'？`"
      detail="这将永久删除该智能体配置，已有的评测任务不会被删除。"
      confirm-label="删除"
      @confirm="handleDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAgentStore } from '@/stores/agents'
import { formatDate, truncate, protocolLabel, protocolTagType, debounce } from '@/utils'
import { StatusBadge, EmptyState, ConfirmDialog } from '@/components'

const store = useAgentStore()
const search = ref('')
const filterProtocol = ref('')
const filterStatus = ref('')
const testingId = ref(null)
const testResult = ref(null)
const showTestDialog = ref(false)
const showDeleteDialog = ref(false)
const deleteTarget = ref(null)

const filteredAgents = computed(() => {
  let list = store.agents
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(a =>
      a.name?.toLowerCase().includes(q) ||
      a.endpoint_url?.toLowerCase().includes(q)
    )
  }
  return list
})

const onSearch = debounce(() => {}, 300)

async function loadAgents() {
  const params = {}
  if (filterProtocol.value) params.protocol = filterProtocol.value
  if (filterStatus.value) params.status = filterStatus.value
  await store.fetchAgents(params)
}

async function handleTest(agent) {
  testingId.value = agent.id
  const result = await store.testAgent(agent.id)
  testResult.value = result
  showTestDialog.value = true
  testingId.value = null
}

function confirmDelete(agent) {
  deleteTarget.value = agent
  showDeleteDialog.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  await store.deleteAgent(deleteTarget.value.id)
  showDeleteDialog.value = false
  deleteTarget.value = null
}

onMounted(() => loadAgents())
</script>

<style scoped>
.agents-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left {
  display: flex;
  gap: 10px;
  align-items: center;
}

.agent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(108, 92, 231, 0.06);
  --el-table-border-color: var(--border-color);
  cursor: pointer;
}

.agent-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.name-text { font-weight: 500; color: var(--text-primary); font-size: 13px; }
.name-url { font-size: 11px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 280px; }

.text-muted { color: var(--text-secondary); font-size: 12px; }

.action-group .el-button {
  color: var(--text-secondary);
  font-size: 14px;
}
.action-group .el-button:hover {
  color: #6C5CE7;
}
.action-group .el-button[type="danger"]:hover {
  color: #FF3D71;
}

/* Test Dialog */
.test-body { display: flex; flex-direction: column; gap: 16px; }
.test-status {
  display: flex; align-items: center; gap: 8px;
  font-size: 15px; font-weight: 600;
}
.test-status.online { color: #00D68F; }
.test-status.offline, .test-status.error { color: #FF3D71; }

.test-details :deep(.el-descriptions__label) {
  background: var(--table-header-bg); color: var(--text-secondary);
}
.test-details :deep(.el-descriptions__content) {
  background: var(--bg-card); color: var(--text-primary);
}

.test-output { display: flex; flex-direction: column; gap: 6px; }
.output-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
.output-text {
  background: var(--bg-sidebar); border: 1px solid var(--border-color); border-radius: 6px;
  padding: 10px; font-size: 12px; color: var(--text-primary);
  max-height: 120px; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
  margin: 0;
}
</style>
