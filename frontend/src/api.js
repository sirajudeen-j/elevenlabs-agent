// Thin API client for the NovaMart backend.
// In dev, leave VITE_API_URL unset and the Vite proxy forwards /api to :8000.
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

async function request(path, options = {}) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const detail = body?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message || `Request failed with status ${resp.status}`
    const err = new Error(message)
    err.status = resp.status
    err.body = body
    throw err
  }
  return body
}

export const api = {
  getProducts: () => request('/api/products'),
  getOrders: () => request('/api/orders'),
  createOrder: (payload) =>
    request('/api/create_order', { method: 'POST', body: JSON.stringify(payload) }),
  lookupOrder: (orderId) =>
    request('/api/lookup_order', { method: 'POST', body: JSON.stringify({ order_id: orderId }) }),
}
