import apiClient from './client'

export async function getLiveness() {
  const { data } = await apiClient.get('/health/live')
  return data
}

export async function getReadiness() {
  const { data } = await apiClient.get('/health/ready')
  return data
}

export async function downloadJobsCsv() {
  const response = await apiClient.get('/exports/jobs.csv', { responseType: 'blob' })
  return response.data
}

export async function downloadApplicationsCsv() {
  const response = await apiClient.get('/exports/applications.csv', { responseType: 'blob' })
  return response.data
}
