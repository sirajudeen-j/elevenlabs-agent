import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext.jsx'

export default function Cart() {
  const { items, setQuantity, removeItem, total } = useCart()

  if (items.length === 0) {
    return (
      <div>
        <h1>Your cart</h1>
        <p>
          Your cart is empty. <Link to="/products">Browse products</Link>
        </p>
      </div>
    )
  }

  return (
    <div>
      <h1>Your cart</h1>
      <table className="cart-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Quantity</th>
            <th>Subtotal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.product_id}>
              <td>{item.name}</td>
              <td>${item.price.toFixed(2)}</td>
              <td>
                <input
                  type="number"
                  min="0"
                  value={item.quantity}
                  onChange={(e) => setQuantity(item.product_id, Number(e.target.value))}
                />
              </td>
              <td>${(item.price * item.quantity).toFixed(2)}</td>
              <td>
                <button className="btn" onClick={() => removeItem(item.product_id)}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="cart-summary">
        <strong>Total: ${total.toFixed(2)}</strong>
        <Link to="/checkout" className="btn btn-primary">
          Proceed to checkout
        </Link>
      </div>
    </div>
  )
}
