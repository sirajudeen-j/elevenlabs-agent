import { useEffect, useState } from 'react'
import { api } from '../api.js'

// Order tracker: status pipeline shown as a stepper per order.
const STEPS = ['processing', 'shipped', 'out_for_delivery', 'delivered']

function statusIndex(status) {
  const i = STEPS.indexOf(status)
  return i === -1 ? 0 : i
}

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [lookupResult, setLookupResult] = useState(null)

  useEffect(() => {
    api
      .getOrders()
      .then(setOrders)
      .catch((e) => setError(e.message))
  }, [])

  const track = async (e) => {
    e.preventDefault()
    setLookupResult(null)
    try {
      const result = await api.lookupOrder(query.trim())
      setLookupResult(
        result.status === 'not_found'
          ? { error: `No order found with ID ${query.trim()}.` }
          : { order: result },
      )
    } catch (err) {
      setLookupResult({ error: err.message })
    }
  }

  return (
    <div>
      <h1>Order tracker</h1>
      <form onSubmit={track} className="tracker-form">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter order ID, e.g. ORD-1001"
          required
        />
        <button className="btn btn-primary">Track</button>
      </form>
      {lookupResult?.error && <p className="error">{lookupResult.error}</p>}
      {lookupResult?.order && <OrderCard order={lookupResult.order} highlight />}

      <h2>All orders</h2>
      {error && <p className="error">Could not load orders: {error}</p>}
      {orders.map((order) => (
        <OrderCard key={order.order_id} order={order} />
      ))}
    </div>
  )
}

function OrderCard({ order, highlight = false }) {
  const current = statusIndex(order.status)
  return (
    <div className={`card order-card ${highlight ? 'highlight' : ''}`}>
      <div className="order-card-header">
        <strong>{order.order_id}</strong>
        <span>Expected delivery: {order.expected_delivery_date}</span>
      </div>
      <div className="stepper">
        {STEPS.map((step, i) => (
          <div key={step} className={`step ${i <= current ? 'done' : ''}`}>
            <span className="dot" />
            <span className="label">{step.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
      <ul>
        {order.items.map((item, i) => (
          <li key={i}>
            {item.qty} × {item.name} — ${(item.price * item.qty).toFixed(2)}
          </li>
        ))}
      </ul>
      <p className="muted">Ship to: {order.shipping_address}</p>
    </div>
  )
}
