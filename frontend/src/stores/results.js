import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { resultApi, feedbackApi, traceApi } from '@/api'

export const useResultStore = defineStore('results', () => {
  const results = ref([])
  const currentResult = ref(null)
  const badcases = ref([])
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({ count: 0, page: 1, pageSize: 20 })
  const currentTrace = ref(null)

  const total = computed(() => pagination.value.count)
  const badcaseCount = computed(() => badcases.value.length)

  async function fetchResults(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await resultApi.list(params)
      results.value = res.results || res
      if (res.count !== undefined) {
        pagination.value.count = res.count
      }
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchResult(id) {
    loading.value = true
    error.value = null
    try {
      currentResult.value = await resultApi.get(id)
      return currentResult.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchBadcases(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await resultApi.badcases(params)
      badcases.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTrace(id) {
    try {
      currentTrace.value = await traceApi.get(id)
      return currentTrace.value
    } catch (e) {
      currentTrace.value = null
      return null
    }
  }

  async function submitFeedback(data) {
    error.value = null
    try {
      return await feedbackApi.create(data)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function updateFeedback(id, data) {
    error.value = null
    try {
      return await feedbackApi.update(id, data)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function exportBadcases(params = {}) {
    try {
      const blob = await resultApi.exportJsonl(params)
      return blob
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  return {
    results, currentResult, badcases, loading, error, pagination, total, badcaseCount,
    currentTrace,
    fetchResults, fetchResult, fetchBadcases, fetchTrace,
    submitFeedback, updateFeedback, exportBadcases,
  }
})
