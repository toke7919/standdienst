import client from './client'

const a = (slug) => `/admin/${slug}`

export const adminApi = {
  // Dashboard
  getDashboard: (slug) => client.get(`${a(slug)}/dashboard`),

  // Instances
  getInstances: (p) => client.get('/admin/instances', { params: p }),
  getInstance: (slug) => client.get(`${a(slug)}/info`),
  createInstance: (data) => client.post('/admin/instances', data),
  updateInstance: (slug, data) => client.put(`${a(slug)}/instance`, data),
  deleteInstance: (slug) => client.delete(`${a(slug)}/instance`),

  // Volunteers
  getVolunteers: (slug, p) => client.get(`${a(slug)}/volunteers`, { params: p }),
  getVolunteer: (slug, id) => client.get(`${a(slug)}/volunteers/${id}`),
  createVolunteer: (slug, data) => client.post(`${a(slug)}/volunteers`, data),
  updateVolunteer: (slug, id, data) => client.put(`${a(slug)}/volunteers/${id}`, data),
  deleteVolunteer: (slug, id) => client.delete(`${a(slug)}/volunteers/${id}`),
  permanentDeleteVolunteer: (slug, id) =>
    client.delete(`${a(slug)}/volunteers/${id}/permanent`),
  resetVolunteerPassword: (slug, id, data) =>
    client.post(`${a(slug)}/volunteers/${id}/reset-password`, data),

  // Stands
  getStands: (slug) => client.get(`${a(slug)}/stands`),
  createStand: (slug, data) => client.post(`${a(slug)}/stands`, data),
  updateStand: (slug, id, data) => client.put(`${a(slug)}/stands/${id}`, data),
  deleteStand: (slug, id) => client.delete(`${a(slug)}/stands/${id}`),
  reorderStands: (slug, ids) => client.put(`${a(slug)}/stands/reorder`, { ids }),

  // Dates
  getDates: (slug) => client.get(`${a(slug)}/dates`),
  createDate: (slug, data) => client.post(`${a(slug)}/dates`, data),
  updateDate: (slug, id, data) => client.put(`${a(slug)}/dates/${id}`, data),
  deleteDate: (slug, id) => client.delete(`${a(slug)}/dates/${id}`),

  // Shifts
  getShifts: (slug, p) => client.get(`${a(slug)}/shifts`, { params: p }),
  createShift: (slug, data) => client.post(`${a(slug)}/shifts`, data),
  updateShift: (slug, id, data) => client.put(`${a(slug)}/shifts/${id}`, data),
  deleteShift: (slug, id) => client.delete(`${a(slug)}/shifts/${id}`),

  // Registrations
  getRegistrations: (slug, p) => client.get(`${a(slug)}/registrations`, { params: p }),
  createRegistration: (slug, data) => client.post(`${a(slug)}/registrations`, data),
  deleteRegistration: (slug, id) => client.delete(`${a(slug)}/registrations/${id}`),

  // Food
  getFoodTypes: (slug) => client.get(`${a(slug)}/food-types`),
  createFoodType: (slug, data) => client.post(`${a(slug)}/food-types`, data),
  updateFoodType: (slug, id, data) => client.put(`${a(slug)}/food-types/${id}`, data),
  deleteFoodType: (slug, id) => client.delete(`${a(slug)}/food-types/${id}`),
  getFoodDonations: (slug, p) => client.get(`${a(slug)}/food-donations`, { params: p }),
  deleteFoodDonation: (slug, id) => client.delete(`${a(slug)}/food-donations/${id}`),

  // Organizers
  getOrganizers: (p) => client.get('/admin/organizers', { params: p }),
  createOrganizer: (data) => client.post('/admin/organizers', data),
  updateOrganizer: (id, data) => client.put(`/admin/organizers/${id}`, data),
  deleteOrganizer: (id) => client.delete(`/admin/organizers/${id}`),
  assignInstances: (id, data) => client.put(`/admin/organizers/${id}/instances`, data),

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
  getGlobalSettings: () => client.get('/admin/settings/global'),
  updateGlobalSettings: (data) => client.put('/admin/settings/global', data),
  getMailSettings: () => client.get('/admin/settings/mail'),
  updateMailSettings: (data) => client.put('/admin/settings/mail', data),

  // Activity log
  getActivityLog: (p) => client.get('/admin/activity', { params: p }),
  getInstanceActivity: (slug, p) =>
    client.get(`${a(slug)}/activity`, { params: p }),

  // Export URLs (direct downloads)
  exportUrl: (slug, format) => `/api/admin/${slug}/export/${format}`,
  exportIcalUrl: (slug) => `/api/admin/${slug}/export/ical`,

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

  // Backup
  createBackup: () => client.post('/admin/backup/create'),
  testSmbConnection: () => client.post('/admin/backup/test-connection'),

  // Update
  checkUpdate: () => client.get('/admin/update/check'),
  applyUpdate: () => client.post('/admin/update/apply'),
}
