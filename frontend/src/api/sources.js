import apiClient from './client'

export async function importGreenhouse(boardToken) {
  const { data } = await apiClient.post('/sources/import/greenhouse', null, {
    params: { board_token: boardToken },
  })
  return data
}

export async function importLever(companySlug) {
  const { data } = await apiClient.post('/sources/import/lever', null, {
    params: { company_slug: companySlug },
  })
  return data
}

export async function importRemotive(search) {
  const params = {}
  if (search) params.search = search
  const { data } = await apiClient.post('/sources/import/remotive', null, { params })
  return data
}

export async function importArbeitnow() {
  const { data } = await apiClient.post('/sources/import/arbeitnow')
  return data
}

export async function listSourceRuns({ limit = 25, offset = 0 } = {}) {
  const { data } = await apiClient.get('/sources/runs', { params: { limit, offset } })
  return data
}
