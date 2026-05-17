import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOrganizer = computed(() => user.value?.role === 'organizer')
  const isStaff = computed(() => isAdmin.value || isOrganizer.value)
  const isVolunteer = computed(() => user.value?.role === 'volunteer')

  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res.data.user
    } catch {
      user.value = null
    }
  }

  async function login(email, password) {
    loading.value = true
    try {
      const res = await authApi.login(email, password)
      if (res.data.requires_2fa) {
        return { requires2fa: true, role: res.data.role }
      }
      user.value = res.data.user
      return { success: true }
    } finally {
      loading.value = false
    }
  }

  async function volunteerLogin(slug, email, password) {
    loading.value = true
    try {
      const res = await authApi.volunteerLogin(slug, email, password)
      user.value = res.data.user
      return { success: true }
    } finally {
      loading.value = false
    }
  }

  async function verify2fa(code) {
    const res = await authApi.verify2fa(code)
    user.value = res.data.user
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      router.push('/')
    }
  }

  // Listen for forced logout (token refresh failure)
  window.addEventListener('auth:logout', () => {
    user.value = null
    router.push('/admin/login')
  })

  return {
    user, loading,
    isLoggedIn, isAdmin, isOrganizer, isStaff, isVolunteer,
    fetchMe, login, volunteerLogin, verify2fa, logout,
  }
})
