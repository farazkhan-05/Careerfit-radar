import apiClient from './client'

export async function triggerWorkflow() {
  const { data } = await apiClient.post('/workflows/run')
  return data
}

export async function listWorkflows({ limit = 25, offset = 0 } = {}) {
  const { data } = await apiClient.get('/workflows', { params: { limit, offset } })
  return data
}

export async function getWorkflowRun(runId) {
  const { data } = await apiClient.get(`/workflows/${encodeURIComponent(runId)}`)
  return data
}
