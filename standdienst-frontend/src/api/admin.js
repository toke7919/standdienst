import client from './client'

const a = (slug) => `/admin/${slug}`

export const adminApi = {
  // Dashboard
  getDashboard: (slug) => client.get(`${a(slug)}/dashboard`),
  getGlobalDashboard: () => client.get('/admin/dashboard/global'),

  // Instances
  getInstances: (p) => client.get('/admin/instances', { params: p }),
  getInstance: (slug) => client.get(`${a(slug)}/info`),
  createInstance: (data) => client.post('/admin/instances', data),
  updateInstance: (id, data) => client.put(`/admin/instances/${id}`, data),
  deleteInstance: (id) => client.delete(`/admin/instances/${id}`),
  clearInstanceData: (slug) => client.delete(`${a(slug)}/clear-data`),

  // Volunteers
  getVolunteers: (slug, p) => client.get(`${a(slug)}/volunteers`, { params: p }),
  getVolunteer: (slug, id) => client.get(`${a(slug)}/volunteers/${id}`),
  getVolunteerDetail: (slug, id) => client.get(`${a(slug)}/volunteers/${id}/detail`),
  createVolunteer: (slug, data) => client.post(`${a(slug)}/volunteers`, data),
  updateVolunteer: (slug, id, data) => client.put(`${a(slug)}/volunteers/${id}`, data),
  deleteVolunteer: (slug, id) => client.delete(`${a(slug)}/volunteers/${id}`),
  permanentDeleteVolunteer: (slug, id) =>
    client.delete(`${a(slug)}/volunteers/${id}/permanent`),
  resetVolunteerPassword: (slug, id, data) =>
    client.post(`${a(slug)}/volunteers/${id}/reset-password`, data),
  sendDsgvoAuskunft: (slug, id) =>
    client.post(`${a(slug)}/volunteers/${id}/dsgvo-auskunft`),

  // Stands
  getStands: (slug) => client.get(`${a(slug)}/stands`),
  createStand: (slug, data) => client.post(`${a(slug)}/stands`, data),
  updateStand: (slug, id, data) => client.put(`${a(slug)}/stands/${id}`, data),
  deleteStand: (slug, id) => client.delete(`${a(slug)}/stands/${id}`),
  reorderStands: (slug, ids) => client.put(`${a(slug)}/stands/reorder`, { order: ids }),

  // Dates
  getDates: (slug, params) => client.get(`${a(slug)}/dates`, { params }),
  createDate: (slug, data) => client.post(`${a(slug)}/dates`, data),
  updateDate: (slug, id, data) => client.put(`${a(slug)}/dates/${id}`, data),
  deleteDate: (slug, id) => client.delete(`${a(slug)}/dates/${id}`),
  duplicateDate: (slug, id, data) => client.post(`${a(slug)}/dates/${id}/duplicate`, data),

  // Shifts
  getShifts: (slug, p) => client.get(`${a(slug)}/shifts`, { params: p }),
  createShift: (slug, data) => client.post(`${a(slug)}/shifts`, data),
  updateShift: (slug, id, data) => client.put(`${a(slug)}/shifts/${id}`, data),
  deleteShift: (slug, id) => client.delete(`${a(slug)}/shifts/${id}`),

  // Registrations
  getRegistrations: (slug, p) => client.get(`${a(slug)}/registrations`, { params: p }),
  getRegistrationGrid: (slug) => client.get(`${a(slug)}/registrations/grid`),
  createRegistration: (slug, data) => client.post(`${a(slug)}/registrations`, data),
  deleteRegistration: (slug, id) => client.delete(`${a(slug)}/registrations/${id}`),

  // Food
  getFoodTypes: (slug) => client.get(`${a(slug)}/food-types`),
  createFoodType: (slug, data) => client.post(`${a(slug)}/food-types`, data),
  updateFoodType: (slug, id, data) => client.put(`${a(slug)}/food-types/${id}`, data),
  deleteFoodType: (slug, id) => client.delete(`${a(slug)}/food-types/${id}`),
  getFoodDonations: (slug, p) => client.get(`${a(slug)}/food-donations`, { params: p }),
  createFoodDonation: (slug, data) => client.post(`${a(slug)}/food-donations`, data),
  updateFoodDonation: (slug, id, data) => client.put(`${a(slug)}/food-donations/${id}`, data),
  deleteFoodDonation: (slug, id) => client.delete(`${a(slug)}/food-donations/${id}`),

  // Organizers
  getOrganizers: (p) => client.get('/admin/organizers', { params: p }),
  createOrganizer: (data) => client.post('/admin/organizers', data),
  updateOrganizer: (id, data) => client.put(`/admin/organizers/${id}`, data),
  deleteOrganizer: (id) => client.delete(`/admin/organizers/${id}`),
  resendOrganizerInvite: (id) => client.post(`/admin/organizers/${id}/resend-invite`),
  assignInstances: (id, instanceIds) => client.put(`/admin/organizers/${id}`, { instance_ids: instanceIds }),

  // Admins
  getAdmins: () => client.get('/admin/admins'),
  createAdmin: (data) => client.post('/admin/admins', data),
  updateAdmin: (id, data) => client.put(`/admin/admins/${id}`, data),
  deleteAdmin: (id) => client.delete(`/admin/admins/${id}`),

  // Settings
  getSiteSettings: (slug) => client.get(`${a(slug)}/settings`),
  updateSiteSettings: (slug, data) => client.put(`${a(slug)}/settings`, data),
  uploadLogo: (slug, formData) =>
    client.post(`${a(slug)}/settings/logo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteLogo: (slug) => client.delete(`${a(slug)}/settings/logo`),
  getGlobalSettings: () => client.get('/admin/settings/global'),
  updateGlobalSettings: (data) => client.put('/admin/settings/global', data),
  getMailSettings: () => client.get('/admin/settings/mail'),
  updateMailSettings: (data) => client.put('/admin/settings/mail', data),
  sendTestMail: (data) => client.post('/admin/settings/mail/test', data),
  sendTypedTestMail: (data) => client.post('/admin/settings/mail/test-type', data),

  // Activity log
  getActivityLog: (p) => client.get('/admin/activity', { params: p }),
  getInstanceActivity: (slug, p) =>
    client.get(`${a(slug)}/activity`, { params: p }),

  // Export URLs (direct downloads)
  exportUrl: (slug, format) => `/api/admin/${slug}/export/${format}`,
  exportIcalUrl: (slug) => `/api/admin/${slug}/export/ical`,
  exportDiensteUrl: (slug, format) => `/api/admin/${slug}/export/${format}/dienste`,
  exportEssenUrl: (slug, format) => `/api/admin/${slug}/export/${format}/essen`,

  // Export (POST – Datumsselektion)
  exportPdfDienste: (slug, data) => client.post(`${a(slug)}/export/pdf/dienste`, data, { responseType: 'blob' }),
  exportPdfEssen: (slug, data) => client.post(`${a(slug)}/export/pdf/essen`, data, { responseType: 'blob' }),
  sendPdfDienste: (slug, data) => client.post(`${a(slug)}/export/pdf/dienste`, data),
  sendPdfEssen: (slug, data) => client.post(`${a(slug)}/export/pdf/essen`, data),

  // Import
  importShiftsCsv: (slug, formData) =>
    client.post(`${a(slug)}/import/shifts/csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importShiftsXlsx: (slug, formData) =>
    client.post(`${a(slug)}/import/shifts/xlsx`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importShiftsOds: (slug, formData) =>
    client.post(`${a(slug)}/import/shifts/ods`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importTemplateCsvUrl: (slug) => `/api/admin/${slug}/import/template/csv`,
  importTemplateXlsxUrl: (slug) => `/api/admin/${slug}/import/template/xlsx`,
  importTemplateOdsUrl: (slug) => `/api/admin/${slug}/import/template/ods`,

  // Backup
  getBackupSettings: () => client.get('/admin/backup/settings'),
  updateBackupSettings: (data) => client.put('/admin/backup/settings', data),
  listBackups: () => client.get('/admin/backup/list'),
  createBackup: (data) => client.post('/admin/backup/create', data || {}),
  downloadBackupUrl: (name) => `/api/admin/backup/${name}/download`,
  uploadBackup: (formData) =>
    client.post('/admin/backup/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteBackup: (name) => client.delete(`/admin/backup/${name}`),
  restoreBackup: (name, data) => client.post(`/admin/backup/${name}/restore`, data || {}),
  getRestoreStatus: (jobId) => client.get(`/admin/backup/restore-status/${jobId}`),
  lockBackup: (name) => client.post(`/admin/backup/${name}/lock`),
  unlockBackup: (name) => client.delete(`/admin/backup/${name}/lock`),

  // Update
  checkUpdate: () => client.get('/admin/update/check'),
  applyUpdate: () => client.post('/admin/update/apply'),

  // Wartungsmodus
  setMaintenance: (enabled) => client.put('/admin/maintenance', { enabled }),
}
