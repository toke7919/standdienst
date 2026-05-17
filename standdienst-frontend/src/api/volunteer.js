import client from './client'

export const volunteerApi = {
  getShifts: (slug) => client.get(`/volunteer/${slug}/shifts`),
  registerShift: (slug, shiftId) =>
    client.post(`/volunteer/${slug}/shifts/${shiftId}/register`),
  unregisterShift: (slug, shiftId) =>
    client.delete(`/volunteer/${slug}/shifts/${shiftId}/register`),
  getMyRegistrations: (slug) => client.get(`/volunteer/${slug}/my-registrations`),
  getFoodDonations: (slug) => client.get(`/volunteer/${slug}/food-donations`),
  addFoodDonation: (slug, data) => client.post(`/volunteer/${slug}/food-donations`, data),
  removeFoodDonation: (slug, donationId) =>
    client.delete(`/volunteer/${slug}/food-donations/${donationId}`),
  updateProfile: (slug, data) => client.put(`/volunteer/${slug}/profile`, data),
  deleteAccount: (slug) => client.delete(`/volunteer/${slug}/profile`),
  getMeineDaten: (slug) => client.get(`/volunteer/${slug}/meine-daten`),
}
