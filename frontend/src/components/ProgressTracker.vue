<template>
  <div class="progress-tracker">
    <div class="progress-header">
      <span class="progress-phase">{{ phaseLabel }}</span>
      <span class="progress-pct">{{ progressPercent }}%</span>
    </div>
    <el-progress
      :percentage="progressPercent"
      :stroke-width="8"
      :color="progressColor"
      :show-text="false"
      class="progress-bar"
    />
    <div class="progress-details">
      <div class="detail-item" v-if="collectTotal > 0">
        <span class="detail-label">Collect</span>
        <span class="detail-value">{{ collectDone }}/{{ collectTotal }}</span>
        <span class="detail-failed" v-if="collectFailed > 0">({{ collectFailed }} failed)</span>
      </div>
      <div class="detail-item" v-if="evalTotal > 0">
        <span class="detail-label">Evaluate</span>
        <span class="detail-value">{{ evalDone }}/{{ evalTotal }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  phase: { type: String, default: 'pending' },
  progress: { type: Number, default: 0 },
  collectDone: { type: Number, default: 0 },
  collectTotal: { type: Number, default: 0 },
  collectFailed: { type: Number, default: 0 },
  evalDone: { type: Number, default: 0 },
  evalTotal: { type: Number, default: 0 },
})

const phaseLabels = {
  pending: 'Waiting...',
  collecting: 'Collecting agent responses...',
  evaluating: 'Running evaluations...',
  storing: 'Saving results...',
  completed: 'Completed',
  failed: 'Failed',
}

const phaseLabel = computed(() => phaseLabels[props.phase] || props.phase)
const progressPercent = computed(() => Math.min(props.progress, 100))

const progressColor = computed(() => {
  if (props.phase === 'failed') return '#FF3D71'
  if (props.phase === 'completed') return '#00D68F'
  return [
    { color: '#6C5CE7', percentage: 30 },
    { color: '#A855F7', percentage: 60 },
    { color: '#00D68F', percentage: 100 },
  ]
})
</script>

<style scoped>
.progress-tracker {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.progress-phase { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.progress-pct { font-size: 14px; color: var(--accent-start); font-weight: 700; }

.progress-bar :deep(.el-progress-bar__outer) {
  background-color: var(--border-color);
}

.progress-details {
  display: flex;
  gap: 24px;
  margin-top: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.detail-label { color: var(--text-secondary); }
.detail-value { color: var(--text-primary); font-weight: 600; }
.detail-failed { color: var(--danger); }
</style>
