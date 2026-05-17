import client from './client'

export const publicApi = {
  getInstances: () => client.get('/public/instances'),
  getInstanceInfo: (slug) => client.get(`/public/${slug}/info`),
  getCaptcha: (slug) => client.get(`/public/${slug}/captcha`),
  register: (slug, data) => client.post(`/public/${slug}/register`, data),
  forgotPassword: (slug, email) =>
    client.post(`/public/${slug}/forgot-password`, { email }),
  resetPassword: (slug, token, password) =>
    client.post(`/public/${slug}/reset-password`, { token, password }),
  getPrivacyPolicy: (slug) => client.get(`/public/${slug}/datenschutz`),
  welcomeInfo: (slug, token) => client.get(`/public/${slug}/welcome/${token}`),
  welcomeSetup: (slug, token, password) =>
    client.post(`/public/${slug}/welcome/${token}`, { password }),
}
