import apiClient from './client'

export async function importApify() {
  const { data } = await apiClient.post('/sources/import/apify')
  return data
}

export async function listSourceRuns({ limit = 25, offset = 0 } = {}) {
  const { data } = await apiClient.get('/sources/runs', { params: { limit, offset } })
  return data
}
