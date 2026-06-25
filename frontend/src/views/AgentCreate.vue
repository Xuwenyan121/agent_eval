<template>
  <div class="agent-form-page">
    <!-- Header -->
    <div class="form-header">
      <el-button text @click="$router.push('/agents')" class="back-btn">
        <el-icon><ArrowLeft /></el-icon>
        返回智能体列表
      </el-button>
      <h2>{{ isEdit ? '编辑智能体' : '新建智能体' }}</h2>
    </div>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="agent-form"
      v-loading="store.loading"
    >
      <!-- Basic Info -->
      <div class="card">
        <h3 class="section-title">基本信息</h3>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="智能体名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：客服机器人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="协议类型" prop="protocol">
              <el-select v-model="form.protocol" style="width: 100%" @change="onProtocolChange">
                <el-option label="HTTP SSE (Streaming)" value="http_sse" />
                <el-option label="HTTP JSON Response" value="http_json" />
                <el-option label="OpenAI Compatible" value="openai_compat" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="18">
            <el-form-item label="端点地址" prop="endpoint_url">
              <el-input v-model="form.endpoint_url" placeholder="https://api.example.com/v1/chat">
                <template #prepend>
                  <el-select v-model="form.method" style="width: 90px">
                    <el-option label="POST" value="POST" />
                    <el-option label="GET" value="GET" />
                    <el-option label="PUT" value="PUT" />
                  </el-select>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="状态">
              <el-switch v-model="form.status" active-value="active" inactive-value="inactive" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- SSE Config (shown only for http_sse) -->
      <div class="card" v-if="form.protocol === 'http_sse'">
        <h3 class="section-title">SSE 流式配置</h3>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="SSE 事件字段" prop="sse_event_field">
              <el-input v-model="form.sse_event_field" placeholder="choices[0].delta.content" />
              <div class="field-hint">从每个 SSE 事件中提取文本内容的 JSON 路径</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束标记" prop="sse_done_marker">
              <el-input v-model="form.sse_done_marker" placeholder="[DONE]" />
              <div class="field-hint">智能体发送的流终止标记</div>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- OpenAI Config (shown only for openai_compat) -->
      <div class="card" v-if="form.protocol === 'openai_compat'">
        <h3 class="section-title">OpenAI 兼容设置</h3>
        <el-alert
          title="OpenAI 兼容端点使用标准 /v1/chat/completions 格式。请在下方 Headers 中配置 API Key。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />
      </div>

      <!-- Request Template -->
      <div class="card">
        <h3 class="section-title">请求模板</h3>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="请求头 (JSON)">
              <el-input
                v-model="headersText"
                type="textarea"
                :rows="5"
                placeholder='{"Content-Type": "application/json", "Authorization": "Bearer xxx"}'
                class="code-input"
              />
              <div class="field-hint" v-if="headersError" style="color: #FF3D71">{{ headersError }}</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="请求体模板 (JSON)">
              <el-input
                v-model="bodyText"
                type="textarea"
                :rows="5"
                placeholder='{"messages": [{"role": "user", "content": "{{query}}"}], "stream": true}'
                class="code-input"
              />
              <div class="field-hint">使用 <code>{{query}}</code>、<code>{{conv_id}}</code>、<code>{{user_id}}</code> 作为模板变量</div>
              <div class="field-hint" v-if="bodyError" style="color: #FF3D71">{{ bodyError }}</div>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Advanced -->
      <div class="card">
        <h3 class="section-title">高级设置</h3>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="超时时间 (秒)" prop="timeout">
              <el-input-number v-model="form.timeout" :min="5" :max="300" :step="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="重试次数" prop="retry_times">
              <el-input-number v-model="form.retry_times" :min="0" :max="10" :step="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="默认用户 ID">
              <el-input v-model="form.default_user_id" placeholder="test_user" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="默认会话 ID">
              <el-input v-model="form.default_conv_id" placeholder="test_conv" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20" v-if="form.protocol === 'http_sse'">
          <el-col :span="6">
            <el-form-item label="流式输出">
              <el-switch v-model="form.stream" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="缓存用户">
              <el-input v-model="form.cache_user" placeholder="可选的缓存用户标识" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="SSL 证书验证">
              <el-switch v-model="form.verify_ssl" active-text="启用" inactive-text="跳过" />
              <div class="field-hint">使用自签名证书时请关闭此项</div>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <el-button @click="$router.push('/agents')">取消</el-button>
        <el-button class="btn-gradient" :loading="store.loading" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建智能体' }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agents'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const store = useAgentStore()

const formRef = ref(null)
const isEdit = computed(() => route.params.id !== undefined)
const headersText = ref('')
const bodyText = ref('')
const headersError = ref('')
const bodyError = ref('')

const form = reactive({
  name: '',
  endpoint_url: '',
  protocol: 'http_sse',
  method: 'POST',
  headers: {},
  body_template: {},
  stream: true,
  sse_event_field: 'choices[0].delta.content',
  sse_done_marker: '[DONE]',
  default_user_id: 'test_user',
  default_conv_id: 'test_conv',
  cache_user: '',
  timeout: 60,
  retry_times: 3,
  verify_ssl: true,
  status: 'active',
})

const rules = {
  name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
  endpoint_url: [
    { required: true, message: '请输入端点地址', trigger: 'blur' },
    { type: 'url', message: '请输入有效的 URL', trigger: 'blur' },
  ],
  protocol: [{ required: true, message: '请选择协议类型', trigger: 'change' }],
  sse_event_field: [{ required: true, message: '请输入 SSE 事件字段', trigger: 'blur' }],
  timeout: [{ required: true, message: '请输入超时时间', trigger: 'blur' }],
}

function onProtocolChange(protocol) {
  if (protocol === 'http_sse') {
    form.stream = true
    form.sse_event_field = 'choices[0].delta.content'
    form.sse_done_marker = '[DONE]'
    bodyText.value = JSON.stringify({ content: '{{query}}', user_id: '{{user_id}}', conv_id: '{{conv_id}}' }, null, 2)
  } else if (protocol === 'http_json') {
    form.stream = false
    bodyText.value = JSON.stringify({ query: '{{query}}', user_id: '{{user_id}}' }, null, 2)
  } else if (protocol === 'openai_compat') {
    form.stream = true
    bodyText.value = JSON.stringify({ messages: [{ role: 'user', content: '{{query}}' }], stream: true }, null, 2)
    headersText.value = JSON.stringify({ 'Content-Type': 'application/json', 'Authorization': 'Bearer YOUR_API_KEY' }, null, 2)
  }
}

function parseJsonFields() {
  headersError.value = ''
  bodyError.value = ''
  let valid = true

  if (headersText.value.trim()) {
    try {
      form.headers = JSON.parse(headersText.value)
    } catch {
      headersError.value = '请求头 JSON 格式无效'
      valid = false
    }
  } else {
    form.headers = {}
  }

  if (bodyText.value.trim()) {
    try {
      form.body_template = JSON.parse(bodyText.value)
    } catch {
      bodyError.value = '请求体模板 JSON 格式无效'
      valid = false
    }
  } else {
    form.body_template = {}
  }

  return valid
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch { return }

  if (!parseJsonFields()) return

  const payload = { ...form }

  try {
    if (isEdit.value) {
      await store.updateAgent(route.params.id, payload)
      ElMessage.success('智能体更新成功')
    } else {
      await store.createAgent(payload)
      ElMessage.success('智能体创建成功')
    }
    router.push('/agents')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '保存智能体失败')
  }
}

// Load agent for edit mode
onMounted(async () => {
  if (isEdit.value) {
    try {
      const agent = await store.fetchAgent(route.params.id)
      Object.assign(form, {
        name: agent.name,
        endpoint_url: agent.endpoint_url,
        protocol: agent.protocol,
        method: agent.method,
        headers: agent.headers || {},
        body_template: agent.body_template || {},
        stream: agent.stream,
        sse_event_field: agent.sse_event_field,
        sse_done_marker: agent.sse_done_marker,
        default_user_id: agent.default_user_id,
        default_conv_id: agent.default_conv_id,
        cache_user: agent.cache_user,
        timeout: agent.timeout,
        retry_times: agent.retry_times,
        verify_ssl: agent.verify_ssl ?? true,
        status: agent.status,
      })
      headersText.value = Object.keys(agent.headers || {}).length > 0 ? JSON.stringify(agent.headers, null, 2) : ''
      bodyText.value = Object.keys(agent.body_template || {}).length > 0 ? JSON.stringify(agent.body_template, null, 2) : ''
    } catch (e) {
      ElMessage.error('加载智能体失败')
      router.push('/agents')
    }
  } else {
    // Set default body template for SSE
    onProtocolChange('http_sse')
  }
})
</script>

<style scoped>
.agent-form-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.form-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.back-btn {
  color: var(--text-secondary) !important;
  font-size: 13px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.field-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}
.field-hint code {
  background: var(--bg-input);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: var(--accent-start);
}

.code-input :deep(.el-textarea__inner) {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 0;
}

/* Element Plus overrides */
.agent-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.agent-form :deep(.el-input-number) {
  width: 100%;
}

.agent-form :deep(.el-descriptions__label) {
  background: var(--table-header-bg);
}
</style>
