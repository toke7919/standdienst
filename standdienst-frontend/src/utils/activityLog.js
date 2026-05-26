// Gemeinsame Definitionen für alle Aktivitätsprotokoll-Views
import {
  CheckCircleIcon, MinusCircleIcon, ShoppingBagIcon, XCircleIcon,
  ArrowRightOnRectangleIcon, ExclamationCircleIcon,
  UserPlusIcon, UserMinusIcon, TrashIcon,
  CogIcon, DocumentTextIcon, UserGroupIcon, ShieldCheckIcon,
} from '@heroicons/vue/24/outline'

export const EVENT_META = {
  shift_register:            { icon: CheckCircleIcon,              label: 'Dienst +',     color: 'bg-green-100 text-green-700' },
  shift_unregister:          { icon: MinusCircleIcon,              label: 'Dienst −',     color: 'bg-orange-100 text-orange-700' },
  food_register:             { icon: ShoppingBagIcon,              label: 'Spende +',      color: 'bg-teal-100 text-teal-700' },
  food_unregister:           { icon: XCircleIcon,                  label: 'Spende −',      color: 'bg-orange-100 text-orange-700' },
  login_success:             { icon: ArrowRightOnRectangleIcon,    label: 'Login ✓',       color: 'bg-blue-100 text-blue-700' },
  login_fail:                { icon: ExclamationCircleIcon,        label: 'Login ✗',       color: 'bg-red-100 text-red-700' },
  volunteer_register:        { icon: UserPlusIcon,                 label: 'Registrierung', color: 'bg-purple-100 text-purple-700' },
  volunteer_delete:          { icon: UserMinusIcon,                label: 'Löschung',      color: 'bg-yellow-100 text-yellow-700' },
  volunteer_permanent_delete:{ icon: TrashIcon,                    label: 'Endlöschung',   color: 'bg-red-100 text-red-700' },
  audit_settings:            { icon: CogIcon,                      label: 'Einstellungen', color: 'bg-yellow-100 text-yellow-700' },
  audit_data:                { icon: DocumentTextIcon,             label: 'Datenverwaltung', color: 'bg-yellow-100 text-yellow-700' },
  audit_organizer:           { icon: UserGroupIcon,                label: 'Organizer',     color: 'bg-indigo-100 text-indigo-700' },
  audit_admin:               { icon: ShieldCheckIcon,              label: 'Admin',         color: 'bg-indigo-100 text-indigo-700' },
}

export const ACTIVITY_CATEGORIES = [
  { key: '',              label: 'Alle',          types: [] },
  { key: 'dienste',       label: 'Dienste',        types: ['shift_register', 'shift_unregister'] },
  { key: 'essensspenden', label: 'Essensspenden',  types: ['food_register', 'food_unregister'] },
  { key: 'anmeldungen',   label: 'Anmeldungen',    types: ['volunteer_register', 'login_success', 'login_fail'] },
  { key: 'loeschungen',   label: 'Löschungen',     types: ['volunteer_delete', 'volunteer_permanent_delete'] },
  { key: 'audit',         label: 'Audit',          types: ['audit_settings', 'audit_data', 'audit_organizer', 'audit_admin'] },
]

export function fmtTime(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) : ''
}
