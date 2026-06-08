import apiClient from './client'

export async function importApify({ query, location } = {}) {
  const payload = {
    query: typeof query === 'string' ? query.trim() : undefined,
    location: typeof location === 'string' ? location.trim() : undefined,
  }
  const { data } = await apiClient.post('/sources/import/apify', payload)
  return data
}

export async function listSourceRuns({ limit = 25, offset = 0 } = {}) {
  const { data } = await apiClient.get('/sources/runs', { params: { limit, offset } })
  return data
}
