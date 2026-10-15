import { Link, NavLink } from 'react-router-dom'
import { useCart } from '../context/CartContext.jsx'

export default function Navbar() {
  const { count } = useCart()
  return (
    <header className="navbar">
      <Link to="/" className="brand">
        NovaMart
      </Link>
      <nav>
        <NavLink to="/products">Products</NavLink>
        <NavLink to="/orders">Order Tracker</NavLink>
        <NavLink to="/cart" className="cart-link">
          Cart{count > 0 && <span className="cart-badge">{count}</span>}
        </NavLink>
      </nav>
    </header>
  )
}
