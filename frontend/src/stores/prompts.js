import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { promptApi } from '@/api'

export const usePromptStore = defineStore('prompts', () => {
  const prompts = ref([])
  const current = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const dryRunResult = ref(null)
  const dryRunLoading = ref(false)

  const total = computed(() => prompts.value.length)
  const activePrompts = computed(() => prompts.value.filter(p => p.is_active))

  async function fetchPrompts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await promptApi.list(params)
      prompts.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPrompt(id) {
    loading.value = true
    error.value = null
    try {
      current.value = await promptApi.get(id)
      return current.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createPrompt(data) {
    error.value = null
    try {
      const prompt = await promptApi.create(data)
      prompts.value.push(prompt)
      return prompt
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function updatePrompt(id, data) {
    error.value = null
    try {
      const prompt = await promptApi.update(id, data)
      const idx = prompts.value.findIndex(p => p.id === id)
      if (idx !== -1) prompts.value[idx] = prompt
      if (current.value?.id === id) current.value = prompt
      return prompt
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function deletePrompt(id) {
    error.value = null
    try {
      await promptApi.delete(id)
      prompts.value = prompts.value.filter(p => p.id !== id)
      if (current.value?.id === id) current.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function duplicatePrompt(id, data) {
    error.value = null
    try {
      const clone = await promptApi.duplicate(id, data)
      prompts.value.push(clone)
      return clone
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function previewPrompt(id, sample) {
    error.value = null
    try {
      return await promptApi.preview(id, { sample })
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function dryRun(data) {
    dryRunLoading.value = true
    error.value = null
    dryRunResult.value = null
    try {
      dryRunResult.value = await promptApi.dryRun(data)
      return dryRunResult.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      dryRunLoading.value = false
    }
  }

  function clearDryRun() {
    dryRunResult.value = null
  }

  return {
    prompts, current, loading, error,
    dryRunResult, dryRunLoading,
    total, activePrompts,
    fetchPrompts, fetchPrompt,
    createPrompt, updatePrompt, deletePrompt,
    duplicatePrompt, previewPrompt,
    dryRun, clearDryRun,
  }
})
