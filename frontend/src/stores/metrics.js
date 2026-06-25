import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { metricApi } from '@/api'

export const useMetricStore = defineStore('metrics', () => {
  const definitions = ref([])
  const metricTypes = ref({})
  const dryRunResult = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const total = computed(() => definitions.value.length)
  const gEvalMetrics = computed(() => definitions.value.filter(m => m.type === 'g_eval'))
  const ruleMetrics = computed(() => definitions.value.filter(m => m.type === 'rule'))
  const builtinMetrics = computed(() => definitions.value.filter(m => m.type === 'deepeval_builtin'))

  async function fetchDefinitions(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await metricApi.list(params)
      definitions.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTypes() {
    try {
      metricTypes.value = await metricApi.types()
      return metricTypes.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      return {}
    }
  }

  async function createDefinition(data) {
    error.value = null
    try {
      const def = await metricApi.create(data)
      definitions.value.push(def)
      return def
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function updateDefinition(id, data) {
    error.value = null
    try {
      const def = await metricApi.update(id, data)
      const idx = definitions.value.findIndex(d => d.id === id)
      if (idx !== -1) definitions.value[idx] = def
      return def
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function deleteDefinition(id) {
    error.value = null
    try {
      await metricApi.delete(id)
      definitions.value = definitions.value.filter(d => d.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function dryRun(data) {
    loading.value = true
    error.value = null
    dryRunResult.value = null
    try {
      const result = await metricApi.dryRun(data)
      dryRunResult.value = result
      return result
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearDryRun() {
    dryRunResult.value = null
  }

  return {
    definitions, metricTypes, dryRunResult, loading, error,
    total, gEvalMetrics, ruleMetrics, builtinMetrics,
    fetchDefinitions, fetchTypes,
    createDefinition, updateDefinition, deleteDefinition,
    dryRun, clearDryRun,
  }
})
