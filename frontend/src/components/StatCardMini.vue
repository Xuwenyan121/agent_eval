<template>
  <div class="stat-card-mini">
    <div class="mini-icon" :style="{ background: iconBg }">
      <el-icon :size="20" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="mini-content">
      <div class="mini-value">{{ displayValue }}</div>
      <div class="mini-label">{{ label }}</div>
    </div>
    <div class="mini-trend" v-if="trend !== undefined" :class="trendClass">
      <el-icon :size="12">
        <component :is="trend >= 0 ? 'Top' : 'Bottom'" />
      </el-icon>
      {{ Math.abs(trend) }}%
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Number, String], required: true },
  label: { type: String, required: true },
  icon: { type: String, default: 'DataLine' },
  iconColor: { type: String, default: '#6C5CE7' },
  trend: { type: Number, default: undefined },
  decimals: { type: Number, default: 0 },
})

const iconBg = computed(() => `${props.iconColor}15`)

const displayValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  return props.decimals > 0 ? props.value.toFixed(props.decimals) : props.value.toString()
})

const trendClass = computed(() => props.trend >= 0 ? 'trend-up' : 'trend-down')
</script>

<style scoped>
.stat-card-mini {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.mini-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mini-content { flex: 1; }
.mini-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.mini-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

.mini-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
}
.trend-up { color: #00D68F; }
.trend-down { color: #FF3D71; }
</style>
