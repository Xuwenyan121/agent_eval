<template>
  <div class="score-ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :viewBox="`0 0 ${size} ${size}`" class="ring-svg">
      <circle
        class="ring-bg"
        :cx="center" :cy="center" :r="radius"
        fill="none" :stroke-width="strokeWidth"
      />
      <circle
        class="ring-fill"
        :cx="center" :cy="center" :r="radius"
        fill="none" :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        :stroke="ringColor"
      />
    </svg>
    <div class="ring-content">
      <span class="ring-value" :style="{ color: ringColor }">{{ displayValue }}</span>
      <span class="ring-label" v-if="label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  maxScore: { type: Number, default: 1 },
  size: { type: Number, default: 100 },
  strokeWidth: { type: Number, default: 6 },
  label: { type: String, default: '' },
  showPercent: { type: Boolean, default: false },
})

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const normalizedScore = computed(() => Math.min(props.score / props.maxScore, 1))
const dashOffset = computed(() => circumference.value * (1 - normalizedScore.value))

const ringColor = computed(() => {
  const pct = normalizedScore.value
  if (pct >= 0.8) return '#00D68F'
  if (pct >= 0.6) return '#FFAA00'
  if (pct >= 0.4) return '#FF8C00'
  return '#FF3D71'
})

const displayValue = computed(() => {
  if (props.showPercent) return `${(normalizedScore.value * 100).toFixed(0)}%`
  return props.score.toFixed(2)
})
</script>

<style scoped>
.score-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.ring-svg {
  transform: rotate(-90deg);
}

.ring-bg {
  stroke: var(--border-color);
}

.ring-fill {
  stroke-linecap: round;
  transition: stroke-dashoffset 0.8s ease, stroke 0.3s;
}

.ring-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ring-value {
  font-weight: 700;
  font-size: v-bind('size * 0.22 + "px"');
}

.ring-label {
  font-size: v-bind('size * 0.12 + "px"');
  color: var(--text-secondary);
  margin-top: 2px;
}
</style>
