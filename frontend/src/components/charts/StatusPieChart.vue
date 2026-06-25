<template>
  <div ref="chartRef" class="chart-container" :style="{ height: height + 'px' }" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  height: { type: Number, default: 240 },
  title: { type: String, default: '' },
})

const chartRef = ref(null)
let chart = null

// Read CSS variable value from the DOM
function getCSSVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const colorMap = {
  pending: '#FFAA00',
  running: '#6C5CE7',
  completed: '#00D68F',
  failed: '#FF3D71',
  cancelled: '#9498A6',
}

const option = () => {
  const textPrimary = getCSSVar('--text-primary') || '#E8E8ED'
  const textSecondary = getCSSVar('--text-secondary') || '#9498A6'
  const bgCard = getCSSVar('--bg-card') || '#1A1D27'
  const borderColor = getCSSVar('--border-color') || '#2A2D3A'

  const pieData = Object.entries(props.data)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      itemStyle: { color: colorMap[name] || '#9498A6' },
    }))

  return {
    title: props.title ? {
      text: props.title,
      left: 'left',
      textStyle: { color: textPrimary, fontSize: 14, fontWeight: 600 },
    } : undefined,
    tooltip: {
      trigger: 'item',
      backgroundColor: bgCard,
      borderColor: borderColor,
      textStyle: { color: textPrimary, fontSize: 12 },
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 8,
      top: 'center',
      textStyle: { color: textSecondary, fontSize: 11 },
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
    },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['35%', '55%'],
      data: pieData,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 600, color: textPrimary },
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' },
      },
      itemStyle: {
        borderColor: bgCard,
        borderWidth: 2,
        borderRadius: 4,
      },
    }],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })
  chart.setOption(option())
}

function handleResize() {
  chart?.resize()
}

// Watch for theme changes by observing class changes on the app container
let themeObserver = null

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)

  // Watch for theme class changes on the app container
  const appEl = document.querySelector('.app-container')
  if (appEl && typeof MutationObserver !== 'undefined') {
    themeObserver = new MutationObserver(() => {
      if (chart) {
        chart.setOption(option())
      }
    })
    themeObserver.observe(appEl, { attributes: true, attributeFilter: ['class'] })
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  themeObserver?.disconnect()
})

watch(() => props.data, () => {
  chart?.setOption(option())
}, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
}
</style>
