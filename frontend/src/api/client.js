import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const apiClient = axios.create({
  baseURL,
  timeout: 30000,
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
    const detail = error.response?.data?.detail
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
