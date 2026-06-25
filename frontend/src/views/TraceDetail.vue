<template>
  <div class="trace-detail-page">
    <!-- Header -->
    <div class="page-header">
      <el-button text @click="goBack" style="color: var(--text-secondary)">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else-if="trace">
      <!-- Overview Stats -->
      <div class="card info-card">
        <div class="info-header">
          <div>
            <h3 class="trace-title">
              <el-icon><Connection /></el-icon>
              Trace：{{ trace.trace_id }}
            </h3>
            <span class="trace-sample">样本：{{ trace.sample_id }}</span>
          </div>
          <el-tag effect="dark" type="info" size="large">{{ trace.total_duration_ms }}ms</el-tag>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">任务</span>
            <span class="info-value link" @click="$router.push(`/tasks/${trace.task}`)">{{ trace.task }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">样本 ID</span>
            <span class="info-value mono">{{ trace.sample_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">总 Token 数</span>
            <span class="info-value accent">{{ trace.total_tokens }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">总耗时</span>
            <span class="info-value">{{ trace.total_duration_ms }}ms</span>
          </div>
          <div class="info-item">
            <span class="info-label">Span 数</span>
            <span class="info-value">{{ (trace.spans || []).length }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">SSE 数据块</span>
            <span class="info-value">{{ (trace.raw_sse_chunks || []).length }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDate(trace.created_at) }}</span>
          </div>
          <div class="info-item" v-if="metaInfo.agent_id">
            <span class="info-label">Agent ID</span>
            <span class="info-value mono accent">{{ metaInfo.agent_id }}</span>
          </div>
          <div class="info-item" v-if="metaInfo.conv_id">
            <span class="info-label">会话 ID</span>
            <span class="info-value mono">{{ metaInfo.conv_id }}</span>
          </div>
          <div class="info-item" v-if="metaInfo.title">
            <span class="info-label">会话标题</span>
            <span class="info-value">{{ metaInfo.title }}</span>
          </div>
        </div>
      </div>

      <!-- Span Timeline -->
      <div class="card" v-if="spans.length">
        <h4 class="section-title">
          Span 时间线
          <span class="count-badge">{{ spans.length }} 个 Span</span>
        </h4>

        <div class="timeline">
          <div v-for="(span, idx) in spans" :key="idx" class="timeline-item">
            <div class="timeline-marker" :class="spanTypeClass(span.type)">
              <span class="marker-num">{{ idx + 1 }}</span>
            </div>
            <div class="timeline-connector" v-if="idx < spans.length - 1"></div>
            <div class="timeline-content">
              <div class="span-header">
                <span class="span-type" :class="spanTypeClass(span.type)">{{ span.type || 'unknown' }}</span>
                <span class="span-duration" v-if="span.duration_ms != null">
                  {{ span.duration_ms }}ms
                  <span class="duration-pct" v-if="trace.total_duration_ms">
                    ({{ ((span.duration_ms / trace.total_duration_ms) * 100).toFixed(0) }}%)
                  </span>
                </span>
              </div>
              <!-- Duration bar -->
              <div class="span-bar-wrap" v-if="span.duration_ms != null">
                <div
                  class="span-bar"
                  :class="spanTypeClass(span.type)"
                  :style="{ width: barWidth(span.duration_ms) + '%' }"
                ></div>
              </div>
              <!-- Meta event info (agentId, convId, title) -->
              <div class="span-meta" v-if="span.type === 'agent.meta'">
                <span class="meta-tag" v-if="span.agent_id">
                  <el-icon><Monitor /></el-icon>
                  Agent ID: {{ span.agent_id }}
                </span>
                <span class="meta-tag" v-if="span.conv_id">
                  <el-icon><ChatLineSquare /></el-icon>
                  Conv ID: {{ span.conv_id }}
                </span>
                <span class="meta-tag" v-if="span.title">
                  <el-icon><Document /></el-icon>
                  Title: {{ span.title }}
                </span>
              </div>
              <!-- Extra info for collect spans -->
              <div class="span-meta" v-else-if="span.chunks != null || span.output">
                <span v-if="span.chunks != null" class="meta-tag">
                  <el-icon><ChatDotRound /></el-icon>
                  {{ span.chunks }} 个数据块
                </span>
              </div>
              <!-- Output preview -->
              <div class="span-output" v-if="span.output">
                <pre class="output-text">{{ truncate(span.output, 300) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Final Output -->
      <div class="card" v-if="trace.final_output">
        <h4 class="section-title">最终输出</h4>
        <pre class="final-output">{{ trace.final_output }}</pre>
      </div>

      <!-- Raw SSE Chunks -->
      <div class="card" v-if="sseChunks.length">
        <h4 class="section-title">
          原始 SSE 数据块
          <span class="count-badge">{{ sseChunks.length }} 个数据块</span>
        </h4>
        <el-collapse>
          <el-collapse-item
            v-for="(chunk, idx) in sseChunks.slice(0, 50)"
            :key="idx"
            :name="idx"
          >
            <template #title>
              <span class="chunk-title">
                数据块 #{{ idx + 1 }}
                <span class="chunk-preview">{{ truncate(String(chunk), 80) }}</span>
              </span>
            </template>
            <pre class="chunk-content">{{ typeof chunk === 'string' ? chunk : JSON.stringify(chunk, null, 2) }}</pre>
          </el-collapse-item>
        </el-collapse>
        <p class="text-muted" v-if="sseChunks.length > 50" style="margin-top: 8px">
          显示前 50 个数据块，共 {{ sseChunks.length }} 个。
        </p>
      </div>

      <!-- Full Trace Data -->
      <div class="card" v-if="hasTraceData">
        <h4 class="section-title">
          Trace 数据（JSON）
          <el-button text size="small" @click="copyTraceData" style="color: var(--accent-start); margin-left: 8px">
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
        </h4>
        <pre class="trace-json">{{ JSON.stringify(trace.trace_data, null, 2) }}</pre>
      </div>

      <!-- Empty state -->
      <div v-if="!spans.length && !trace.final_output && !sseChunks.length && !hasTraceData" class="card">
        <EmptyState
          icon="Connection"
          title="Trace 为空"
          description="该 Trace 没有记录到 Span 数据、输出或 SSE 数据块。"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResultStore } from '@/stores/results'
import { formatDate, truncate } from '@/utils'
import { EmptyState } from '@/components'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const store = useResultStore()

const traceId = route.params.id
const loading = ref(true)

const trace = computed(() => store.currentTrace)
const spans = computed(() => trace.value?.spans || [])
const sseChunks = computed(() => trace.value?.raw_sse_chunks || [])
const hasTraceData = computed(() => trace.value?.trace_data && Object.keys(trace.value.trace_data).length > 0)

// Extract meta info from trace_data or spans
const metaInfo = computed(() => {
  // First check trace_data (full meta object)
  if (trace.value?.trace_data && typeof trace.value.trace_data === 'object') {
    const td = trace.value.trace_data
    if (td.agentId || td.convId || td.title) {
      return {
        agent_id: td.agentId || '',
        conv_id: td.convId || '',
        title: td.title || '',
      }
    }
  }
  // Fallback: find meta span
  const metaSpan = spans.value.find(s => s.type === 'agent.meta')
  if (metaSpan) {
    return {
      agent_id: metaSpan.agent_id || '',
      conv_id: metaSpan.conv_id || '',
      title: metaSpan.title || '',
    }
  }
  return {}
})

function barWidth(durationMs) {
  if (!trace.value?.total_duration_ms) return 0
  return Math.min((durationMs / trace.value.total_duration_ms) * 100, 100)
}

function spanTypeClass(type) {
  if (!type) return 'type-default'
  const t = type.toLowerCase()
  if (t.includes('collect') || t.includes('request') || t.includes('call')) return 'type-collect'
  if (t.includes('eval') || t.includes('score') || t.includes('judge')) return 'type-eval'
  if (t.includes('stream') || t.includes('sse') || t.includes('chunk')) return 'type-stream'
  if (t.includes('meta') || t.includes('info')) return 'type-meta'
  if (t.includes('error') || t.includes('fail')) return 'type-error'
  return 'type-default'
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/reports')
  }
}

function copyTraceData() {
  navigator.clipboard.writeText(JSON.stringify(trace.value.trace_data, null, 2))
  ElMessage.success('Trace 数据已复制')
}

onMounted(async () => {
  loading.value = true
  try {
    await store.fetchTrace(traceId)
    if (!trace.value) {
      ElMessage.error('Trace 未找到')
      router.back()
    }
  } catch {
    ElMessage.error('加载 Trace 失败')
    router.back()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.trace-detail-page { display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; justify-content: space-between; align-items: center; }

.loading-wrap { padding: 20px; }

/* Info Card */
.info-card { background: linear-gradient(135deg, var(--bg-card) 0%, var(--info-card-gradient-end) 100%); }
.info-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.trace-title {
  font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0;
  display: flex; align-items: center; gap: 8px;
}
.trace-title .el-icon { color: var(--accent-start); }
.trace-sample { color: var(--text-secondary); font-size: 12px; font-family: monospace; margin-top: 4px; display: block; }

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.accent { color: var(--accent-start); font-weight: 700; }
.info-value.mono { font-family: monospace; font-size: 12px; }
.info-value.link { color: var(--accent-start); cursor: pointer; }
.info-value.link:hover { text-decoration: underline; }

/* Section */
.section-title {
  color: var(--text-primary); font-size: 14px; margin: 0 0 16px;
  display: flex; align-items: center; gap: 8px;
}
.count-badge {
  background: rgba(108, 92, 231, 0.15); color: var(--accent-start);
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
}

/* Timeline */
.timeline { position: relative; }
.timeline-item { display: flex; gap: 14px; position: relative; padding-bottom: 16px; }
.timeline-item:last-child { padding-bottom: 0; }

.timeline-marker {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff; flex-shrink: 0; z-index: 1;
}
.marker-num { line-height: 1; }

.type-collect { background: var(--accent-start); }
.type-eval { background: #00D68F; }
.type-stream { background: #FFAA00; }
.type-meta { background: #3B82F6; }
.type-error { background: #FF3D71; }
.type-default { background: #4A4D5A; }

.timeline-connector {
  position: absolute; left: 15px; top: 32px; bottom: 0;
  width: 2px; background: var(--border-color);
}

.timeline-content { flex: 1; min-width: 0; }
.span-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 6px;
}
.span-type {
  font-size: 13px; font-weight: 600; text-transform: capitalize;
  padding: 2px 8px; border-radius: 4px; color: #fff;
}
.span-type.type-collect { background: rgba(108, 92, 231, 0.2); color: var(--accent-start); }
.span-type.type-eval { background: rgba(0, 214, 143, 0.2); color: #00D68F; }
.span-type.type-stream { background: rgba(255, 170, 0, 0.2); color: #FFAA00; }
.span-type.type-meta { background: rgba(59, 130, 246, 0.15); color: #3B82F6; }
.span-type.type-error { background: rgba(255, 61, 113, 0.2); color: #FF3D71; }
.span-type.type-default { background: rgba(74, 77, 90, 0.3); color: var(--text-secondary); }

.span-duration { font-size: 13px; color: var(--text-primary); font-weight: 600; }
.duration-pct { font-size: 11px; color: var(--text-secondary); font-weight: 400; }

.span-bar-wrap {
  height: 6px; background: var(--border-color); border-radius: 3px; overflow: hidden;
  margin-bottom: 8px;
}
.span-bar { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.span-bar.type-collect { background: linear-gradient(90deg, var(--accent-start), #A855F7); }
.span-bar.type-eval { background: linear-gradient(90deg, #00D68F, #34D399); }
.span-bar.type-stream { background: linear-gradient(90deg, #FFAA00, #FBBF24); }
.span-bar.type-error { background: linear-gradient(90deg, #FF3D71, #F87171); }
.span-bar.type-default { background: #4A4D5A; }

.span-meta { display: flex; gap: 12px; margin-bottom: 6px; }
.meta-tag {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-secondary);
}

.span-output {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 6px;
  padding: 8px; margin-top: 4px;
}
.output-text {
  font-size: 12px; color: var(--text-primary); font-family: monospace;
  white-space: pre-wrap; word-break: break-all; margin: 0;
  max-height: 100px; overflow: hidden;
}

/* Final Output */
.final-output {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px;
  padding: 14px; font-size: 13px; color: var(--text-primary); font-family: monospace;
  white-space: pre-wrap; word-break: break-all; margin: 0;
  max-height: 400px; overflow: auto;
}

/* SSE Chunks */
.chunk-title { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.chunk-preview { color: var(--text-secondary); font-size: 11px; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
.chunk-content {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 6px;
  padding: 10px; font-size: 12px; color: var(--text-primary); font-family: monospace;
  white-space: pre-wrap; word-break: break-all; margin: 0;
  max-height: 300px; overflow: auto;
}

:deep(.el-collapse) {
  --el-collapse-header-bg-color: transparent;
  --el-collapse-content-bg-color: transparent;
  --el-collapse-header-text-color: var(--text-primary);
  --el-collapse-content-text-color: var(--text-primary);
  --el-collapse-header-height: 40px;
  border-color: var(--border-color);
}
:deep(.el-collapse-item__header) { border-color: var(--border-color); }
:deep(.el-collapse-item__wrap) { border-color: var(--border-color); }

/* Trace JSON */
.trace-json {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px;
  padding: 14px; font-size: 12px; color: var(--text-primary); font-family: monospace;
  white-space: pre-wrap; word-break: break-all; margin: 0;
  max-height: 500px; overflow: auto;
}

.text-muted { color: var(--text-secondary); font-size: 12px; }
</style>
