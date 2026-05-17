import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

let _refreshing = null

function getCsrfToken() {
  const match = document.cookie.match(/csrf_access_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

client.interceptors.request.use((config) => {
  const csrf = getCsrfToken()
  if (csrf && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRF-TOKEN'] = csrf
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (
      err.response?.status === 401 &&
      err.response?.data?.code === 'token_expired' &&
      !original._retry
    ) {
      original._retry = true
      if (!_refreshing) {
        _refreshing = client.post('/auth/refresh').finally(() => { _refreshing = null })
      }
      try {
        await _refreshing
        return client(original)
      } catch {
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(err)
      }
    }
    return Promise.reject(err)
  }
)

export default client
