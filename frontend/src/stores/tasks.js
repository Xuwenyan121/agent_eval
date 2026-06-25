import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api'

export const useTaskStore = defineStore('tasks', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const taskProgress = ref({})
  const loading = ref(false)
  const error = ref(null)

  const total = computed(() => tasks.value.length)
  const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
  const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.list(params)
      tasks.value = res.results || res
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    loading.value = true
    error.value = null
    try {
      currentTask.value = await taskApi.get(id)
      return currentTask.value
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    loading.value = true
    error.value = null
    try {
      const task = await taskApi.create(data)
      tasks.value.unshift(task)
      return task
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function runTask(id) {
    error.value = null
    try {
      const result = await taskApi.run(id)
      // Update local task status
      const task = tasks.value.find(t => t.id === id)
      if (task) task.status = 'running'
      if (currentTask.value?.id === id) currentTask.value.status = 'running'
      return result
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function stopTask(id) {
    error.value = null
    try {
      await taskApi.stop(id)
      const task = tasks.value.find(t => t.id === id)
      if (task) task.status = 'cancelled'
      if (currentTask.value?.id === id) currentTask.value.status = 'cancelled'
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    }
  }

  async function fetchProgress(id) {
    try {
      const progress = await taskApi.progress(id)
      taskProgress.value[id] = progress
      return progress
    } catch (e) {
      return null
    }
  }

  async function compareTasks(taskIds) {
    loading.value = true
    error.value = null
    try {
      return await taskApi.compare(taskIds)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(id) {
    loading.value = true
    error.value = null
    try {
      await taskApi.delete(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    tasks, currentTask, taskProgress, loading, error,
    total, runningCount, completedCount,
    fetchTasks, fetchTask, createTask, deleteTask,
    runTask, stopTask, fetchProgress, compareTasks,
  }
})
