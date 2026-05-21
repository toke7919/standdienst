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

  // Passkey
  passkeyRegisterBegin: () => client.post('/auth/passkey/register/begin'),
  passkeyRegisterComplete: (credential) => client.post('/auth/passkey/register/complete', credential),
  passkeyAuthenticateBegin: () => client.post('/auth/passkey/authenticate/begin'),
  passkeyAuthenticateComplete: (credential) =>
    client.post('/auth/passkey/authenticate/complete', credential),
  passkeyList: () => client.get('/auth/passkey/credentials'),
  passkeyDelete: (id) => client.delete(`/auth/passkey/credentials/${id}`),
  updateProfile: (data) => client.put('/auth/profile', data),
}
