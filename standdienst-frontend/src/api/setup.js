import client from './client'

export const setupApi = {
  status: () => client.get('/setup/status'),
  createAdmin: (data) => client.post('/setup/admin', data),
  saveConfig: (data) => client.post('/setup/config', data),
  saveMail: (data) => client.post('/setup/mail', data),
  finish: () => client.post('/setup/finish'),
}
