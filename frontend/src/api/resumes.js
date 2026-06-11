import apiClient from './client'

export async function uploadResume(file, extractProfile = true) {
  const form = new FormData()
  form.append('file', file)
  form.append('extract_profile', String(extractProfile))
  const { data } = await apiClient.post('/resumes/upload', form)
  return data
}

export async function listResumes(limit = 50, offset = 0) {
  const { data } = await apiClient.get('/resumes', { params: { limit, offset } })
  return data
}

export async function getResume(resumeId) {
  const { data } = await apiClient.get(`/resumes/${resumeId}`)
  return data
}

export async function deleteResume(resumeId) {
  await apiClient.delete(`/resumes/${resumeId}`)
}

export async function deleteAllResumes() {
  await apiClient.delete('/resumes', { headers: { 'X-Confirm-Bulk-Delete': 'true' } })
}
