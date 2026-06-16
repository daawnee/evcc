// Fixed EUR -> HUF rate used to prefill EV purchase prices from the catalog's new-price.
export const EUR_HUF = 400

export async function getModels() {
  const r = await fetch('/models')
  if (!r.ok) throw new Error('Nem sikerült betölteni a modelleket')
  return r.json()
}

export async function getCar(modelId) {
  const r = await fetch('/car/' + encodeURIComponent(modelId))
  if (!r.ok) return null
  return r.json()
}

export async function calculate(body) {
  const r = await fetch('/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function photoUrl(modelId) {
  return '/photo/' + encodeURIComponent(modelId)
}
