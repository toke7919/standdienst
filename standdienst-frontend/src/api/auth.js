import client from './client'

export const authApi = {
  login: (email, password) => client.post('/auth/login', { email, password }),
  volunteerLogin: (slug, email, password) =>
    client.post('/auth/volunteer-login', { slug, email, password }),
  verify2fa: (code) => client.post('/auth/2fa/verify', { code }),
  setup2fa: () => client.post('/auth/2fa/setup'),
  confirm2fa: (code) => client.post('/auth/2fa/confirm', { code }),
  disable2fa: () => client.post('/auth/2fa/disable'),
  logout: () => client.post('/auth/logout'),
  me: () => client.get('/auth/me'),
  forgotPassword: (email, type = 'admin') =>
    client.post('/auth/forgot-password', { email, type }),
  resetPassword: (token, password, type = 'admin') =>
    client.post('/auth/reset-password', { token, password, type }),
}
