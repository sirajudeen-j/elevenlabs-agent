import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useCart } from '../context/CartContext.jsx'

export default function Products() {
  const [products, setProducts] = useState([])
  const [category, setCategory] = useState('All')
  const [error, setError] = useState(null)
  const { addItem } = useCart()

  useEffect(() => {
    api
      .getProducts()
      .then(setProducts)
      .catch((e) => setError(e.message))
  }, [])

  const categories = ['All', ...new Set(products.map((p) => p.category))]
  const visible = category === 'All' ? products : products.filter((p) => p.category === category)

  if (error) return <p className="error">Could not load products: {error}</p>

  return (
    <div>
      <h1>Products</h1>
      <div className="filters">
        {categories.map((c) => (
          <button
            key={c}
            className={`btn btn-filter ${c === category ? 'active' : ''}`}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>
      <div className="product-grid">
        {visible.map((p) => (
          <div key={p.id} className="product-card">
            <img src={p.image} alt={p.name} />
            <h3>{p.name}</h3>
            <p>{p.description}</p>
            <p className="price">${p.price.toFixed(2)}</p>
            <button className="btn btn-primary" onClick={() => addItem(p)}>
              Add to cart
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
