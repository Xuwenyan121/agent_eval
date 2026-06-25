import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/api'

export const useAgentStore = defineStore('agents', () => {
  const agents = ref([])
  const currentAgent = ref(null)
  const protocols = ref([])
  const loading = ref(false)
  const error = ref(null)
  const testResult = ref(null)
  const testing = ref(false)

  const total = computed(() => agents.value.length)
  const activeCount = computed(() => agents.value.filter(a => a.status === 'active').length)

  async function fetchAgents(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await agentApi.list(params)
      agents.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchAgent(id) {
    loading.value = true
    error.value = null
    try {
      currentAgent.value = await agentApi.get(id)
      return currentAgent.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchProtocols() {
    try {
      const res = await agentApi.protocols()
      protocols.value = res.protocols || res
      return protocols.value
    } catch (e) {
      return []
    }
  }

  async function createAgent(data) {
    loading.value = true
    error.value = null
    try {
      const agent = await agentApi.create(data)
      agents.value.unshift(agent)
      return agent
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateAgent(id, data) {
    loading.value = true
    error.value = null
    try {
      const agent = await agentApi.update(id, data)
      const idx = agents.value.findIndex(a => a.id === id)
      if (idx !== -1) agents.value[idx] = agent
      if (currentAgent.value?.id === id) currentAgent.value = agent
      return agent
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteAgent(id) {
    loading.value = true
    error.value = null
    try {
      await agentApi.delete(id)
      agents.value = agents.value.filter(a => a.id !== id)
      if (currentAgent.value?.id === id) currentAgent.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testAgent(id) {
    testing.value = true
    testResult.value = null
    try {
      const result = await agentApi.test(id)
      testResult.value = result
      return result
    } catch (e) {
      testResult.value = { status: 'offline', error: e.response?.data?.error || e.message, latency_ms: 0, sample_output: '', sse_chunks_received: 0 }
      return testResult.value
    } finally {
      testing.value = false
    }
  }

  function clearTestResult() {
    testResult.value = null
  }

  return {
    agents, currentAgent, protocols, loading, error, testResult, testing,
    total, activeCount,
    fetchAgents, fetchAgent, fetchProtocols,
    createAgent, updateAgent, deleteAgent, testAgent, clearTestResult,
  }
})
