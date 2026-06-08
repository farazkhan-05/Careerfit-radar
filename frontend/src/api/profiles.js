import apiClient from './client'

export async function listProfiles(limit = 50, offset = 0) {
  const { data } = await apiClient.get('/profiles', { params: { limit, offset } })
  return data
}

export async function getProfile(profileId) {
  const { data } = await apiClient.get(`/profiles/${profileId}`)
  return data
}

export async function deleteProfile(profileId) {
  await apiClient.delete(`/profiles/${profileId}`)
}

export async function deleteAllProfiles() {
  await apiClient.delete('/profiles')
}

export async function scoreJobs() {
  const { data } = await apiClient.post('/profiles/score-jobs')
  return data
}
