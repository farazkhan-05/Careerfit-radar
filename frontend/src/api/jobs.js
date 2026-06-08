import apiClient from './client'

export async function listJobs({ limit = 50, offset = 0, q, status, source, top_matches } = {}) {
  const params = { limit, offset }
  if (q) params.q = q
  if (status) params.status = status
  if (source) params.source = source
  if (top_matches) params.top_matches = true
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

export async function deleteJob(jobId) {
  await apiClient.delete(`/jobs/${jobId}`)
}

export async function deleteAllJobs() {
  await apiClient.delete('/jobs')
}
