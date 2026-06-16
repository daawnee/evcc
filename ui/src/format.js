import { locale, t } from './i18n.js'

const grouped = new Intl.NumberFormat(locale)

// Prices are in Hungarian forint regardless of UI language; show grouped number + "Ft" suffix
// (using the active locale's grouping) rather than a currency symbol.
export function fmtFt(v) {
  return grouped.format(Math.round(v || 0)) + ' Ft'
}

export function fmtFtShort(v) {
  const m = Math.round(((v || 0) / 1_000_000) * 10) / 10
  return m.toLocaleString(locale) + ' M Ft'
}

export function fmtNum(v) {
  return grouped.format(v || 0)
}

// Years with the locale's decimal separator (en: 7.8, hu: 7,8).
export function monthsToYears(m) {
  return (m / 12).toLocaleString(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

export const TYPE_LABEL = t.types

// "As new", "1 month", "1 year 2 months" / "Újként", "1 hónap", "1 év 2 hónap"
export function ageLabel(months) {
  if (!months) return t.age.asNew
  const y = Math.floor(months / 12)
  const mo = months % 12
  const parts = []
  if (y > 0) parts.push(`${y} ${y === 1 ? t.age.year : t.age.years}`)
  if (mo > 0) parts.push(`${mo} ${mo === 1 ? t.age.month : t.age.months}`)
  return parts.join(' ')
}
