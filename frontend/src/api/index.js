import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Request interceptor: attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: unwrap data, handle auth errors
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

// ─── Agent Endpoints ──────────────────────────────────────────────
export const agentApi = {
  list: (params) => apiClient.get('/agents/', { params }),
  get: (id) => apiClient.get(`/agents/${id}/`),
  create: (data) => apiClient.post('/agents/', data),
  update: (id, data) => apiClient.put(`/agents/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/agents/${id}/`, data),
  delete: (id) => apiClient.delete(`/agents/${id}/`),
  test: (id, payload) => apiClient.post(`/agents/${id}/test/`, payload || {}),
  protocols: () => apiClient.get('/agents/protocols/'),
}

// ─── Dataset Endpoints ────────────────────────────────────────────
export const datasetApi = {
  list: (params) => apiClient.get('/datasets/', { params }),
  get: (id) => apiClient.get(`/datasets/${id}/`),
  create: (data) => apiClient.post('/datasets/', data),
  update: (id, data) => apiClient.put(`/datasets/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/datasets/${id}/`, data),
  delete: (id) => apiClient.delete(`/datasets/${id}/`),
  samples: (id, params) => apiClient.get(`/datasets/${id}/samples/`, { params }),
  addSample: (id, data) => apiClient.post(`/datasets/${id}/add_sample/`, data),
  updateSample: (id, sampleId, data) => apiClient.put(`/datasets/${id}/samples/${sampleId}/`, data),
  deleteSample: (id, sampleId) => apiClient.delete(`/datasets/${id}/samples/${sampleId}/`),
  upload: (id, formData) => apiClient.post(`/datasets/${id}/upload/`, formData, {
    timeout: 120000,
  }),
  version: (id, data) => apiClient.post(`/datasets/${id}/create_version/`, data),
}

// ─── Task Endpoints ───────────────────────────────────────────────
export const taskApi = {
  list: (params) => apiClient.get('/tasks/', { params }),
  get: (id) => apiClient.get(`/tasks/${id}/`),
  create: (data) => apiClient.post('/tasks/', data),
  update: (id, data) => apiClient.put(`/tasks/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/tasks/${id}/`, data),
  delete: (id) => apiClient.delete(`/tasks/${id}/`),
  run: (id) => apiClient.post(`/tasks/${id}/run/`),
  stop: (id) => apiClient.post(`/tasks/${id}/stop/`),
  progress: (id) => apiClient.get(`/tasks/${id}/progress/`),
  compare: (taskIds) => apiClient.post('/tasks/compare_tasks/', { task_ids: taskIds }),
  badcaseAnalysis: (id) => apiClient.get(`/tasks/${id}/badcase-analysis/`),
  // BadCase Collection
  collectBadcases: (id, data) => apiClient.post(`/tasks/${id}/badcases/collect/`, data || {}),
  listBadcases: (id, params) => apiClient.get(`/tasks/${id}/badcases/`, { params }),
  getBadcaseDetail: (taskId, feedbackId) => apiClient.get(`/tasks/${taskId}/badcases/${feedbackId}/`),
  badcaseStats: (id) => apiClient.get(`/tasks/${id}/badcases/stats/`),
}

// ─── Result Endpoints ─────────────────────────────────────────────
export const resultApi = {
  list: (params) => apiClient.get('/results/', { params }),
  filter: (data) => apiClient.post('/results/filter/', data),
  get: (id) => apiClient.get(`/results/${id}/`),
  badcases: (params) => apiClient.get('/results/badcases/', { params }),
  exportJsonl: (params) => apiClient.get('/results/export_jsonl/', {
    params,
    responseType: 'blob',
  }),
  exportExcel: (params) => apiClient.get('/results/export_excel/', {
    params,
    responseType: 'blob',
  }),
}

// ─── Trace Endpoints ──────────────────────────────────────────────
export const traceApi = {
  list: (params) => apiClient.get('/traces/', { params }),
  get: (traceId) => apiClient.get(`/traces/${traceId}/`),
}

// ─── Feedback (BadCase) Endpoints ─────────────────────────────────
export const feedbackApi = {
  list: (params) => apiClient.get('/feedback/', { params }),
  get: (id) => apiClient.get(`/feedback/${id}/`),
  create: (data) => apiClient.post('/feedback/', data),
  update: (id, data) => apiClient.put(`/feedback/${id}/`, data),
  delete: (id) => apiClient.delete(`/feedback/${id}/`),
}

// ─── BadCase Collection Rules ─────────────────────────────────────
export const badcaseRuleApi = {
  list: (params) => apiClient.get('/badcase-rules/', { params }),
  get: (id) => apiClient.get(`/badcase-rules/${id}/`),
  create: (data) => apiClient.post('/badcase-rules/', data),
  update: (id, data) => apiClient.put(`/badcase-rules/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/badcase-rules/${id}/`, data),
  delete: (id) => apiClient.delete(`/badcase-rules/${id}/`),
  test: (id, data) => apiClient.post(`/badcase-rules/${id}/test/`, data),
}

// ─── Metric Endpoints ─────────────────────────────────────────────
export const metricApi = {
  list: (params) => apiClient.get('/metrics/', { params }),
  get: (id) => apiClient.get(`/metrics/${id}/`),
  create: (data) => apiClient.post('/metrics/', data),
  update: (id, data) => apiClient.put(`/metrics/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/metrics/${id}/`, data),
  delete: (id) => apiClient.delete(`/metrics/${id}/`),
  types: () => apiClient.get('/metrics/types/'),
  dryRun: (data) => apiClient.post('/metrics/dry-run/', data),
}

// ─── Judge Prompt Endpoints ────────────────────────────────────────
export const promptApi = {
  list: (params) => apiClient.get('/prompts/', { params }),
  get: (id) => apiClient.get(`/prompts/${id}/`),
  create: (data) => apiClient.post('/prompts/', data),
  update: (id, data) => apiClient.put(`/prompts/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/prompts/${id}/`, data),
  delete: (id) => apiClient.delete(`/prompts/${id}/`),
  duplicate: (id, data) => apiClient.post(`/prompts/${id}/duplicate/`, data || {}),
  preview: (id, data) => apiClient.post(`/prompts/${id}/preview/`, data || {}),
  dryRun: (data) => apiClient.post('/prompts/dry-run/', data),
}

// ─── Judge Model Configs ──────────────────────────────────────────
export const judgeModelApi = {
  list: (params) => apiClient.get('/judge-models/', { params }),
  get: (id) => apiClient.get(`/judge-models/${id}/`),
  create: (data) => apiClient.post('/judge-models/', data),
  update: (id, data) => apiClient.put(`/judge-models/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/judge-models/${id}/`, data),
  delete: (id) => apiClient.delete(`/judge-models/${id}/`),
  setDefault: (id) => apiClient.post(`/judge-models/${id}/set-default/`),
  duplicate: (id) => apiClient.post(`/judge-models/${id}/duplicate/`),
  test: (data) => apiClient.post('/judge-models/test/', data),
}

// ─── Dashboard / Stats ────────────────────────────────────────────
export const dashboardApi = {
  async getStats() {
    const [agents, datasets, tasks, badcases, metrics] = await Promise.all([
      agentApi.list({ page_size: 100 }).catch(() => ({ count: 0, results: [] })),
      datasetApi.list({ page_size: 1 }).catch(() => ({ count: 0, results: [] })),
      taskApi.list({ page_size: 50, ordering: '-created_at' }).catch(() => ({ count: 0, results: [] })),
      resultApi.badcases({ page_size: 1 }).catch(() => ({ count: 0 })),
      metricApi.list({ page_size: 1 }).catch(() => ({ count: 0 })),
    ])

    const allTasks = tasks.results || []
    const allAgents = agents.results || []

    const statusDist = { pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0 }
    allTasks.forEach(t => {
      const s = t.status?.toLowerCase()
      if (s in statusDist) statusDist[s]++
    })

    const completedTasks = allTasks.filter(t => t.status === 'completed' && t.overall_score != null)
    const avgScore = completedTasks.length > 0
      ? completedTasks.reduce((sum, t) => sum + (t.overall_score || 0), 0) / completedTasks.length
      : null

    const now = new Date()
    const trendDays = 7
    const trendLabels = []
    const trendCounts = []
    for (let i = trendDays - 1; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      const dateStr = d.toISOString().slice(0, 10)
      trendLabels.push(d.toLocaleDateString('en', { month: 'short', day: 'numeric' }))
      trendCounts.push(allTasks.filter(t => t.created_at?.slice(0, 10) === dateStr).length)
    }

    const scoreBuckets = { '0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0, '0.6-0.8': 0, '0.8-1.0': 0 }
    completedTasks.forEach(t => {
      const s = t.overall_score || 0
      if (s < 0.2) scoreBuckets['0-0.2']++
      else if (s < 0.4) scoreBuckets['0.2-0.4']++
      else if (s < 0.6) scoreBuckets['0.4-0.6']++
      else if (s < 0.8) scoreBuckets['0.6-0.8']++
      else scoreBuckets['0.8-1.0']++
    })

    return {
      agentCount: agents.count || allAgents.length,
      activeAgentCount: allAgents.filter(a => a.status === 'active').length,
      datasetCount: datasets.count || 0,
      taskCount: tasks.count || allTasks.length,
      badcaseCount: badcases.count || 0,
      metricCount: metrics.count || 0,
      avgScore,
      completedCount: completedTasks.length,
      runningCount: statusDist.running,
      statusDistribution: statusDist,
      scoreDistribution: scoreBuckets,
      trendLabels,
      trendCounts,
      recentTasks: allTasks.slice(0, 10),
      agents: allAgents.slice(0, 5),
    }
  },
}