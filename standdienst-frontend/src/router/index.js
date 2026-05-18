import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSetupStore } from '@/stores/setup'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Setup-Assistent (vor allen anderen Routen ausgewertet)
    {
      path: '/setup',
      component: () => import('@/views/setup/SetupWizard.vue'),
      meta: { setupOnly: true },
    },

    // Public
    {
      path: '/',
      component: () => import('@/views/public/Landing.vue'),
    },
    {
      path: '/impressum',
      component: () => import('@/views/public/Impressum.vue'),
    },

    // Admin auth
    {
      path: '/admin/login',
      component: () => import('@/views/admin/Login.vue'),
      meta: { guest: true },
    },
    {
      path: '/admin/login/2fa',
      component: () => import('@/views/admin/TwoFAVerify.vue'),
      meta: { guest: true },
    },
    {
      path: '/admin/reset-password',
      component: () => import('@/views/admin/ResetPassword.vue'),
    },
    {
      path: '/admin/forgot-password',
      component: () => import('@/views/admin/ForgotPassword.vue'),
    },

    // Admin area
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, requiresStaff: true },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: () => import('@/views/admin/Dashboard.vue') },
        { path: ':slug/dashboard', component: () => import('@/views/admin/Dashboard.vue') },
        { path: 'instances', component: () => import('@/views/admin/Instances.vue') },
        { path: 'organizers', component: () => import('@/views/admin/Organizers.vue') },
        { path: 'admins', component: () => import('@/views/admin/Admins.vue') },
        { path: 'settings/global', component: () => import('@/views/admin/settings/Global.vue') },
        { path: 'settings/mail', component: () => import('@/views/admin/settings/Mail.vue') },
        { path: 'activity', component: () => import('@/views/admin/ActivityLog.vue') },
        { path: 'backup', component: () => import('@/views/admin/Backup.vue') },
        { path: 'update', component: () => import('@/views/admin/Update.vue') },
        { path: 'profile/2fa', component: () => import('@/views/admin/TwoFASetup.vue') },
        { path: 'profile/passkeys', component: () => import('@/views/admin/PasskeySettings.vue') },
        // Instanz-spezifisch
        { path: ':slug/volunteers', component: () => import('@/views/admin/Volunteers.vue') },
        { path: ':slug/stands', component: () => import('@/views/admin/Stands.vue') },
        { path: ':slug/dates', component: () => import('@/views/admin/Dates.vue') },
        { path: ':slug/shifts', component: () => import('@/views/admin/Shifts.vue') },
        { path: ':slug/registrations', component: () => import('@/views/admin/Registrations.vue') },
        { path: ':slug/food', component: () => import('@/views/admin/Food.vue') },
        { path: ':slug/settings', component: () => import('@/views/admin/settings/Instance.vue') },
        { path: ':slug/export', component: () => import('@/views/admin/Export.vue') },
        { path: ':slug/import', component: () => import('@/views/admin/Import.vue') },
        { path: ':slug/activity', component: () => import('@/views/admin/InstanceActivity.vue') },
      ],
    },

    // Volunteer-Bereich
    {
      path: '/:slug/login',
      component: () => import('@/views/volunteer/Login.vue'),
    },
    {
      path: '/:slug/register',
      component: () => import('@/views/volunteer/Register.vue'),
    },
    {
      path: '/:slug/forgot-password',
      component: () => import('@/views/volunteer/ForgotPassword.vue'),
    },
    {
      path: '/:slug/reset-password',
      component: () => import('@/views/volunteer/ResetPassword.vue'),
    },
    {
      path: '/:slug/welcome/:token',
      component: () => import('@/views/volunteer/WelcomeSetup.vue'),
    },
    {
      path: '/:slug/datenschutz',
      component: () => import('@/views/public/PrivacyPolicy.vue'),
    },
    {
      path: '/:slug',
      component: () => import('@/layouts/VolunteerLayout.vue'),
      meta: { requiresAuth: true, requiresVolunteer: true },
      children: [
        { path: '', redirect: (to) => `/${to.params.slug}/shifts` },
        { path: 'shifts', component: () => import('@/views/volunteer/Shifts.vue') },
        { path: 'my-shifts', component: () => import('@/views/volunteer/MyShifts.vue') },
        { path: 'food', component: () => import('@/views/volunteer/FoodDonations.vue') },
        { path: 'profile', component: () => import('@/views/volunteer/Profile.vue') },
        { path: 'impressum', component: () => import('@/views/public/Impressum.vue') },
        { path: 'datenschutz', component: () => import('@/views/public/PrivacyPolicy.vue') },
      ],
    },

    // 404
    { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFound.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const setup = useSetupStore()
  const setupDone = await setup.check()

  // Setup-Seite: nur wenn Setup noch nicht abgeschlossen
  if (to.meta.setupOnly) {
    if (setupDone) return '/'
    return // Weiterleiten zum Wizard
  }

  // Alle anderen Seiten: Setup muss zuerst abgeschlossen sein
  if (!setupDone) return '/setup'

  // Standard Auth-Guards
  const auth = useAuthStore()
  if (auth.isLoggedIn === false && (to.meta.requiresAuth || to.meta.requiresStaff)) {
    await auth.fetchMe()
  }

  if (to.meta.requiresStaff && !auth.isStaff) return '/admin/login'
  if (to.meta.requiresVolunteer && !auth.isVolunteer) return `/${to.params.slug}/login`

  if (to.meta.guest && auth.isLoggedIn) {
    if (auth.isStaff) return '/admin/dashboard'
    if (auth.isVolunteer) return `/${auth.user.instance_slug || ''}`
  }
})

export default router
