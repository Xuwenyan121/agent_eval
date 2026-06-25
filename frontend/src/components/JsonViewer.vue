<template>
  <div class="json-viewer">
    <div class="json-header" v-if="title">
      <span class="json-title">{{ title }}</span>
      <el-button size="small" text @click="copyContent" class="copy-btn">
        <el-icon><DocumentCopy /></el-icon>
        {{ copied ? 'Copied' : 'Copy' }}
      </el-button>
    </div>
    <pre class="json-content" ref="jsonRef"><code>{{ formatted }}</code></pre>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: { type: [Object, Array, String], required: true },
  title: { type: String, default: '' },
})

const jsonRef = ref(null)
const copied = ref(false)

const formatted = computed(() => {
  try {
    if (typeof props.data === 'string') {
      return JSON.stringify(JSON.parse(props.data), null, 2)
    }
    return JSON.stringify(props.data, null, 2)
  } catch {
    return String(props.data)
  }
})

async function copyContent() {
  try {
    await navigator.clipboard.writeText(formatted.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}
</script>

<style scoped>
.json-viewer {
  background: var(--code-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.json-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}
.json-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.copy-btn { color: var(--text-secondary) !important; font-size: 12px; }

.json-content {
  padding: 12px;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-primary);
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
</style>
