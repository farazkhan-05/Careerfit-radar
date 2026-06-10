import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL,
  timeout: 120000,
})

apiClient.interceptors.request.use((config) => {
  if (!(config.data instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timed out. Resume parsing or profile extraction is taking longer than expected.'))
    }

    if (!error.response) {
      return Promise.reject(
        new Error(
          `Backend is unreachable at ${baseURL}. Make sure the API server is running, then restart the frontend dev server if needed.`,
        ),
      )
    }

    const detail = error.response?.data?.detail
    if (!detail && error.response.status >= 500) {
      return Promise.reject(
        new Error(
          `Backend request failed at ${baseURL}. Make sure the API server is running and healthy before uploading.`,
        ),
      )
    }

    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg ?? d).join(', ')
          : error.message ?? 'An unexpected error occurred'
    return Promise.reject(new Error(message))
  },
)

export default apiClient
