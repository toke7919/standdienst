/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        ink:       'rgb(var(--color-ink-rgb) / <alpha-value>)',
        muted:     'var(--color-muted)',
        sand:      'var(--color-sand)',
        'bg-brand': 'var(--color-bg)',
        'bg-warm':  'var(--color-bg-warm)',
        soft:      'var(--color-soft)',
        primary: {
          50:  'var(--primary-50)',
          100: 'var(--primary-100)',
          200: 'var(--primary-200)',
          300: 'var(--primary-300)',
          400: 'var(--primary-400)',
          500: 'var(--primary-500)',
          600: 'var(--primary-600)',
          700: 'var(--primary-700)',
          800: 'var(--primary-800)',
          900: 'var(--primary-900)',
          950: 'var(--primary-950)',
        },
      },
    },
  },
  plugins: [],
}
