<template>
  <div class="metric-config">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMetricStore } from '@/stores/metrics'
import { EmptyState } from '@/components'

const store = useMetricStore()

const filterCategory = ref('')
const filterType = ref('')

const categoryLabels = { business_dim: '业务维度', ml_metric: 'ML 指标', multimodal: '多模态' }
const categoryLabel = (c) => categoryLabels[c] || c
const categoryTag = (c) => ({ business_dim: 'primary', ml_metric: 'success', multimodal: 'warning' })[c] || 'info'
const typeLabels = { g_eval: 'G-Eval (LLM)', rule: '规则类', custom: '自定义', deepeval_builtin: 'DeepEval' }
const typeLabel = (t) => typeLabels[t] || t
const typeTag = (t) => ({ g_eval: 'primary', rule: 'success', custom: 'warning' })[t] || 'info'

async function loadMetrics() {
  const params = {}
  if (filterCategory.value) params.category = filterCategory.value
  if (filterType.value) params.type = filterType.value
  await store.fetchDefinitions(params)
}

onMounted(async () => {
  await loadMetrics()
  await store.fetchTypes()
})
</script>

<style scoped>
.metric-config { display: flex; flex-direction: column; gap: 14px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
</style>