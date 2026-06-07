import apiClient from './client'

export async function listJobs({ limit = 50, offset = 0, q, status, source } = {}) {
  const params = { limit, offset }
  if (q) params.q = q
  if (status) params.status = status
  if (source) params.source = source
  const { data } = await apiClient.get('/jobs', { params })
  return data
}

export async function getJob(jobId) {
  const { data } = await apiClient.get(`/jobs/${jobId}`)
  return data
}

export async function createManualJob(payload) {
  const { data } = await apiClient.post('/jobs/manual', payload)
  return data
}

export async function updateJob(jobId, patch) {
  const { data } = await apiClient.patch(`/jobs/${jobId}`, patch)
  return data
}
