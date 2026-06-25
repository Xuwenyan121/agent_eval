import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { datasetApi } from '@/api'

export const useDatasetStore = defineStore('datasets', () => {
  const datasets = ref([])
  const currentDataset = ref(null)
  const samples = ref([])
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({ count: 0, page: 1 })

  const total = computed(() => datasets.value.length)
  const totalSamples = computed(() => datasets.value.reduce((sum, d) => sum + (d.sample_count || 0), 0))

  async function fetchDatasets(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await datasetApi.list(params)
      datasets.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchDataset(id) {
    loading.value = true
    error.value = null
    try {
      currentDataset.value = await datasetApi.get(id)
      return currentDataset.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createDataset(data) {
    loading.value = true
    error.value = null
    try {
      const dataset = await datasetApi.create(data)
      datasets.value.unshift(dataset)
      return dataset
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateDataset(id, data) {
    loading.value = true
    error.value = null
    try {
      const dataset = await datasetApi.update(id, data)
      const idx = datasets.value.findIndex(d => d.id === id)
      if (idx !== -1) datasets.value[idx] = dataset
      if (currentDataset.value?.id === id) currentDataset.value = dataset
      return dataset
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteDataset(id) {
    loading.value = true
    error.value = null
    try {
      await datasetApi.delete(id)
      datasets.value = datasets.value.filter(d => d.id !== id)
      if (currentDataset.value?.id === id) currentDataset.value = null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function uploadSamples(datasetId, formData) {
    loading.value = true
    error.value = null
    try {
      const result = await datasetApi.upload(datasetId, formData)
      await fetchDataset(datasetId)
      return result
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSamples(datasetId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await datasetApi.samples(datasetId, params)
      samples.value = res.results || res
      if (res.count !== undefined) pagination.value.count = res.count
      return res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function addSample(datasetId, data) {
    error.value = null
    try {
      const sample = await datasetApi.addSample(datasetId, data)
      samples.value.unshift(sample)
      await fetchDataset(datasetId)
      return sample
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function updateSample(datasetId, sampleId, data) {
    error.value = null
    try {
      const sample = await datasetApi.updateSample(datasetId, sampleId, data)
      const idx = samples.value.findIndex(s => s.id === sampleId)
      if (idx !== -1) samples.value[idx] = sample
      return sample
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function deleteSample(datasetId, sampleId) {
    error.value = null
    try {
      await datasetApi.deleteSample(datasetId, sampleId)
      samples.value = samples.value.filter(s => s.id !== sampleId)
      await fetchDataset(datasetId)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function createVersion(datasetId, data) {
    loading.value = true
    error.value = null
    try {
      const newDataset = await datasetApi.version(datasetId, data)
      datasets.value.unshift(newDataset)
      return newDataset
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    datasets, currentDataset, samples, loading, error, pagination,
    total, totalSamples,
    fetchDatasets, fetchDataset, createDataset, updateDataset, deleteDataset,
    uploadSamples, fetchSamples, addSample, updateSample, deleteSample,
    createVersion,
  }
})
