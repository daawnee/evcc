const huf = new Intl.NumberFormat('hu-HU', {
  style: 'currency',
  currency: 'HUF',
  maximumFractionDigits: 0,
})
const plain = new Intl.NumberFormat('hu-HU')

export function fmtFt(v) {
  return huf.format(Math.round(v || 0))
}

export function fmtFtShort(v) {
  const m = (v || 0) / 1_000_000
  return plain.format(Math.round(m * 10) / 10) + ' M Ft'
}

export function fmtNum(v) {
  return plain.format(v || 0)
}

export function monthsToYears(m) {
  return (m / 12).toFixed(1).replace('.', ',')
}

// Hungarian labels for the powertrain types.
export const TYPE_LABEL = {
  bev: 'Elektromos',
  petrol: 'Benzin',
  diesel: 'Dízel',
  hybrid: 'Hibrid',
  phev: 'Plug-in hibrid',
}
