import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useCart } from '../context/CartContext.jsx'

export default function Checkout() {
  const { items, total, clear } = useCart()
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  if (items.length === 0) {
    return (
      <p>
        Your cart is empty. <Link to="/products">Browse products</Link>
      </p>
    )
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await api.createOrder({
        items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
        customer_email: email,
        shipping_address: address,
        // Optional: links the order to an account so the voice agent is
        // allowed to change the shipping address after verification.
        ...(accountNumber ? { account_number: accountNumber } : {}),
      })
      clear()
      navigate(`/order-confirmation/${result.order_id}`)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="checkout">
      <h1>Checkout</h1>
      <p>
        {items.length} item(s), total <strong>${total.toFixed(2)}</strong> — delivery in 3 days.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="customer@example.com"
          />
        </label>
        <label>
          Shipping address
          <textarea
            required
            minLength={5}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="123 Market Street, San Francisco, CA 94107"
          />
        </label>
        <label>
          Account number (optional — enables voice support for this order)
          <input
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value)}
            placeholder="e.g. 10000001"
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Placing order…' : 'Place order'}
        </button>
      </form>
    </div>
  )
}
