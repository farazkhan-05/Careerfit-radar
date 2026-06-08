import apiClient from './client'

export async function listApplications({ limit = 50, offset = 0, status } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  const { data } = await apiClient.get('/applications', { params })
  return data
}

export async function saveJob(jobId) {
  const { data } = await apiClient.post(`/applications/jobs/${jobId}/save`)
  return data
}

export async function updateApplication(applicationId, patch) {
  const { data } = await apiClient.patch(`/applications/${applicationId}`, patch)
  return data
}

export async function deleteApplication(applicationId) {
  await apiClient.delete(`/applications/${applicationId}`)
}

export async function deleteAllApplications() {
  await apiClient.delete('/applications')
}
