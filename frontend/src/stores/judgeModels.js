import { defineStore } from 'pinia'
import { judgeModelApi } from '@/api'

export const useJudgeModelStore = defineStore('judgeModels', {
  state: () => ({
    models: [],
    current: null,
    loading: false,
    error: null,
    testResult: null,
    testLoading: false,
  }),

  getters: {
    activeModels: (state) => state.models.filter(m => m.is_active),
    defaultModel: (state) => state.models.find(m => m.is_default) || null,
    providers: (state) => [...new Set(state.models.map(m => m.provider))],
  },

  actions: {
    async fetchModels(params = {}) {
      this.loading = true
      this.error = null
      try {
        const resp = await judgeModelApi.list(params)
        this.models = resp.results || resp.data?.results || []
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
      } finally {
        this.loading = false
      }
    },

    async fetchModel(id) {
      this.loading = true
      this.error = null
      try {
        const resp = await judgeModelApi.get(id)
        this.current = resp
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
      } finally {
        this.loading = false
      }
    },

    async createModel(data) {
      this.loading = true
      this.error = null
      try {
        const resp = await judgeModelApi.create(data)
        this.models.unshift(resp)
        return resp
      } catch (e) {
        this.error = e.response?.data || e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async updateModel(id, data) {
      this.loading = true
      this.error = null
      try {
        const resp = await judgeModelApi.update(id, data)
        const idx = this.models.findIndex(m => m.id === id)
        if (idx !== -1) this.models[idx] = resp
        if (this.current?.id === id) this.current = resp
        return resp
      } catch (e) {
        this.error = e.response?.data || e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async deleteModel(id) {
      this.loading = true
      this.error = null
      try {
        await judgeModelApi.delete(id)
        this.models = this.models.filter(m => m.id !== id)
        if (this.current?.id === id) this.current = null
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },

    async setDefault(id) {
      try {
        await judgeModelApi.setDefault(id)
        this.models.forEach(m => { m.is_default = m.id === id })
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      }
    },

    async duplicateModel(id) {
      try {
        const resp = await judgeModelApi.duplicate(id)
        this.models.unshift(resp)
        return resp
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      }
    },

    async testModel(data) {
      this.testLoading = true
      this.testResult = null
      try {
        const resp = await judgeModelApi.test(data)
        this.testResult = resp
        return resp
      } catch (e) {
        this.testResult = e.response?.data || { success: false, error: e.message }
        throw e
      } finally {
        this.testLoading = false
      }
    },

    clearTestResult() {
      this.testResult = null
    },
  },
})
