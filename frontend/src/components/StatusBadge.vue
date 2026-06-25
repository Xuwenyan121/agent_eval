<template>
  <span class="status-badge" :class="[statusClass, { pulse: isRunning }]">
    <span class="status-dot" />
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  type: { type: String, default: 'task' }, // 'task' | 'agent' | 'sample'
})

const statusMap = {
  // Task statuses
  pending: { label: 'Pending', class: 'pending' },
  queued: { label: 'Queued', class: 'pending' },
  running: { label: 'Running', class: 'running' },
  collecting: { label: 'Collecting', class: 'running' },
  evaluating: { label: 'Evaluating', class: 'running' },
  completed: { label: 'Completed', class: 'completed' },
  success: { label: 'Success', class: 'completed' },
  failed: { label: 'Failed', class: 'failed' },
  error: { label: 'Error', class: 'failed' },
  cancelled: { label: 'Cancelled', class: 'cancelled' },
  stopped: { label: 'Stopped', class: 'cancelled' },
  // Agent statuses
  active: { label: 'Active', class: 'completed' },
  inactive: { label: 'Inactive', class: 'cancelled' },
  offline: { label: 'Offline', class: 'failed' },
  // Sample statuses
  passed: { label: 'Passed', class: 'completed' },
  pass: { label: 'Pass', class: 'completed' },
  fail: { label: 'Fail', class: 'failed' },
}

const statusInfo = computed(() => statusMap[props.status?.toLowerCase()] || { label: props.status, class: 'pending' })
const label = computed(() => statusInfo.value.label)
const statusClass = computed(() => statusInfo.value.class)
const isRunning = computed(() => ['running', 'collecting', 'evaluating'].includes(props.status?.toLowerCase()))
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.pending { background: var(--badge-pending-bg); color: var(--warning); }
.running { background: var(--badge-running-bg); color: var(--accent-start); }
.completed { background: var(--badge-success-bg); color: var(--success); }
.failed { background: var(--badge-danger-bg); color: var(--danger); }
.cancelled { background: rgba(148, 152, 166, 0.15); color: var(--text-secondary); }

.pulse .status-dot {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
