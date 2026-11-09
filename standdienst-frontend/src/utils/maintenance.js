// Wartungsmodus-Regeln, geteilt von Router-Guard, App.vue und Wartungsseite.

const UNAVAILABLE_STATUS = [502, 503, 504]
const LOGIN_PATHS = ['/admin/login', '/admin/login/2fa']

// Antwortet die API nicht (z. B. Container-/Dienst-Neustart während eines Updates),
// zeigen wir die Wartungsseite statt Fehlermeldungen.
export function isApiUnavailable(err) {
  if (err?.response) return UNAVAILABLE_STATUS.includes(err.response.status)
  if (err?.code === 'ERR_CANCELED') return false
  return !!err?.request
}

// Während der Wartung erreichbar: Admin-Login (für alle) und Admin-Bereich (nur Global-Admins).
export function mayBypassMaintenance(path, isGlobalAdmin) {
  if (LOGIN_PATHS.includes(path)) return true
  return isGlobalAdmin && (path === '/admin' || path.startsWith('/admin/'))
}
