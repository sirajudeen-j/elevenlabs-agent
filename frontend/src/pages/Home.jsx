import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useCart } from '../context/CartContext.jsx'

export default function Home() {
  const [featured, setFeatured] = useState([])
  const { addItem } = useCart()

  useEffect(() => {
    api.getProducts().then((products) => setFeatured(products.slice(0, 3))).catch(() => {})
  }, [])

  return (
    <div>
      <section className="hero">
        <h1>Welcome to NovaMart</h1>
        <p>
          Electronics and home goods, delivered in 3 days. Need a hand? Talk to
          Nova, our voice assistant, using the button in the corner.
        </p>
        <Link to="/products" className="btn btn-primary">
          Shop products
        </Link>
      </section>
      <section>
        <h2>Featured</h2>
        <div className="product-grid">
          {featured.map((p) => (
            <div key={p.id} className="product-card">
              <img src={p.image} alt={p.name} />
              <h3>{p.name}</h3>
              <p className="price">${p.price.toFixed(2)}</p>
              <button className="btn" onClick={() => addItem(p)}>
                Add to cart
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
