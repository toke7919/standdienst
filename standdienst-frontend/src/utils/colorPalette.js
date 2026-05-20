function hexToHsl(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l * 100]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h
  switch (max) {
    case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
    case g: h = ((b - r) / d + 2) / 6; break
    default: h = ((r - g) / d + 4) / 6
  }
  return [h * 360, s * 100, l * 100]
}

function hslToHex(h, s, l) {
  s /= 100; l /= 100
  const a = s * Math.min(l, 1 - l)
  const f = (n) => {
    const k = (n + h / 30) % 12
    return Math.round(255 * (l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)))
      .toString(16).padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

function clamp(v, lo = 0, hi = 100) {
  return Math.max(lo, Math.min(hi, v))
}

// Behandelt den Eingabe-Hex als Shade 600 und leitet die vollständige Skala ab.
export function generatePalette(hex) {
  const [h, s, l] = hexToHsl(hex)

  const lighter = (lt, st) =>
    hslToHex(h, clamp(s * st), clamp(l + (97 - l) * lt))
  const darker = (delta) =>
    hslToHex(h, clamp(s * 1.05), clamp(l + delta, 4))

  return {
    50:  lighter(1.00, 0.12),
    100: lighter(0.90, 0.22),
    200: lighter(0.76, 0.40),
    300: lighter(0.60, 0.60),
    400: lighter(0.40, 0.80),
    500: lighter(0.18, 0.93),
    600: hex,
    700: darker(-9),
    800: darker(-20),
    900: darker(-33),
    950: darker(-45),
  }
}

const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]

export function applyTheme(hex) {
  if (!hex || !/^#[0-9a-fA-F]{6}$/i.test(hex)) return
  const palette = generatePalette(hex)
  const root = document.documentElement
  SHADES.forEach((s) => root.style.setProperty(`--primary-${s}`, palette[s]))
}

export function resetTheme() {
  const root = document.documentElement
  SHADES.forEach((s) => root.style.removeProperty(`--primary-${s}`))
}

// Gibt true zurück wenn auf dem Hex-Hintergrund weiße Schrift besser lesbar ist.
export function isColorDark(hex) {
  if (!hex || !/^#[0-9a-fA-F]{6}$/i.test(hex)) return true
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const toLin = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
  const L = 0.2126 * toLin(r) + 0.7152 * toLin(g) + 0.0722 * toLin(b)
  return L < 0.35
}
