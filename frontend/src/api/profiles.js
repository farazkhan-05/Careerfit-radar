import apiClient from './client'

export async function listProfiles(limit = 50, offset = 0) {
  const { data } = await apiClient.get('/profiles', { params: { limit, offset } })
  return data
}

export async function getProfile(profileId) {
  const { data } = await apiClient.get(`/profiles/${profileId}`)
  return data
}
