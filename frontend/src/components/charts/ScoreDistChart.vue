<template>
  <div ref="chartRef" class="chart-container" :style="{ height: height + 'px' }" />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, TitleComponent, TooltipComponent, GridComponent, CanvasRenderer])

const props = defineProps({
  labels: { type: Array, default: () => [] },
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 280 },
  title: { type: String, default: '' },
})

const chartRef = ref(null)
let chart = null

// Read CSS variable value from the DOM
function getCSSVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const barColors = ['#FF3D71', '#FF8C00', '#FFAA00', '#6C5CE7', '#00D68F']

const option = () => {
  const textPrimary = getCSSVar('--text-primary') || '#E8E8ED'
  const textSecondary = getCSSVar('--text-secondary') || '#9498A6'
  const bgCard = getCSSVar('--bg-card') || '#1A1D27'
  const borderColor = getCSSVar('--border-color') || '#2A2D3A'

  return {
    title: props.title ? {
      text: props.title,
      left: 'left',
      textStyle: { color: textPrimary, fontSize: 14, fontWeight: 600 },
    } : undefined,
    tooltip: {
      trigger: 'axis',
      backgroundColor: bgCard,
      borderColor: borderColor,
      textStyle: { color: textPrimary, fontSize: 12 },
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: 40,
      right: 16,
      top: props.title ? 40 : 16,
      bottom: 28,
    },
    xAxis: {
      type: 'category',
      data: props.labels,
      axisLine: { lineStyle: { color: borderColor } },
      axisLabel: { color: textSecondary, fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: borderColor, type: 'dashed' } },
      axisLabel: { color: textSecondary, fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: props.data.map((val, i) => ({
        value: val,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: barColors[i % barColors.length] },
            { offset: 1, color: barColors[i % barColors.length] + '40' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      })),
      barWidth: '50%',
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

watch(() => [props.labels, props.data], () => {
  chart?.setOption(option())
}, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
}
</style>
