<template>
  <div class="metric-card" :class="{ passed: isPassed, failed: !isPassed && score !== null }">
    <div class="metric-header">
      <span class="metric-name">{{ name }}</span>
      <span class="metric-weight" v-if="weight !== undefined">w={{ weight.toFixed(2) }}</span>
    </div>
    <div class="metric-body">
      <div class="metric-score" :class="scoreClass">
        {{ scoreDisplay }}
      </div>
      <div class="metric-threshold" v-if="threshold !== undefined">
        threshold: {{ threshold.toFixed(2) }}
      </div>
    </div>
    <div class="metric-reason" v-if="reason">
      {{ truncatedReason }}
    </div>
    <div class="metric-bar">
      <div class="metric-bar-fill" :style="{ width: barWidth, background: barColor }" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  score: { type: Number, default: null },
  weight: { type: Number, default: undefined },
  threshold: { type: Number, default: undefined },
  reason: { type: String, default: '' },
  maxScore: { type: Number, default: 1.0 },
})

const scoreDisplay = computed(() => {
  if (props.score === null || props.score === undefined) return '—'
  return props.score.toFixed(3)
})

const isPassed = computed(() => {
  if (props.score === null || props.threshold === undefined) return null
  return props.score >= props.threshold
})

const scoreClass = computed(() => {
  if (props.score === null) return 'na'
  if (isPassed.value === true) return 'pass'
  if (isPassed.value === false) return 'fail'
  return ''
})

const barWidth = computed(() => {
  if (props.score === null) return '0%'
  return `${Math.min((props.score / props.maxScore) * 100, 100)}%`
})

const barColor = computed(() => {
  if (props.score === null) return '#9498A6'
  if (isPassed.value === true) return '#00D68F'
  return '#FF3D71'
})

const truncatedReason = computed(() => {
  if (!props.reason) return ''
  return props.reason.length > 120 ? props.reason.substring(0, 120) + '...' : props.reason
})
</script>

<style scoped>
.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  transition: border-color 0.2s, background-color 0.3s ease;
}
.metric-card:hover { border-color: var(--accent-start); }
.metric-card.passed { border-left: 3px solid var(--success); }
.metric-card.failed { border-left: 3px solid var(--danger); }

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.metric-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.metric-weight { font-size: 11px; color: var(--text-secondary); }

.metric-body {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}
.metric-score { font-size: 22px; font-weight: 700; }
.metric-score.pass { color: var(--success); }
.metric-score.fail { color: var(--danger); }
.metric-score.na { color: var(--text-secondary); }
.metric-threshold { font-size: 11px; color: var(--text-secondary); }

.metric-reason {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: 8px;
}

.metric-bar {
  height: 3px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}
.metric-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}
</style>
