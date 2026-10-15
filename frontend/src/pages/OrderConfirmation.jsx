import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'

export default function OrderConfirmation() {
  const { orderId } = useParams()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .lookupOrder(orderId)
      .then((result) => {
        if (result.status === 'not_found') setError(`Order ${orderId} was not found.`)
        else setOrder(result)
      })
      .catch((e) => setError(e.message))
  }, [orderId])

  if (error) return <p className="error">{error}</p>
  if (!order) return <p>Loading order…</p>

  return (
    <div className="confirmation">
      <h1>Order confirmed</h1>
      <p>
        Thanks for your order! Your order ID is <strong>{order.order_id}</strong> — keep it
        handy, you can ask Nova about it any time.
      </p>
      <div className="order-summary card">
        <p>
          <strong>Status:</strong> {order.status}
        </p>
        <p>
          <strong>Expected delivery:</strong> {order.expected_delivery_date}
        </p>
        <p>
          <strong>Shipping to:</strong> {order.shipping_address}
        </p>
        <ul>
          {order.items.map((item, i) => (
            <li key={i}>
              {item.qty} × {item.name} — ${(item.price * item.qty).toFixed(2)}
            </li>
          ))}
        </ul>
      </div>
      <Link to="/orders" className="btn">
        Track your orders
      </Link>
    </div>
  )
}
