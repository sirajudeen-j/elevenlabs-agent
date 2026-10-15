import { createContext, useContext, useEffect, useMemo, useState } from 'react'

// Cart state is shared across every page via this context and persisted to
// localStorage so a refresh (or a detour to talk to Nova) doesn't lose it.
const CartContext = createContext(null)
const STORAGE_KEY = 'novamart_cart'

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? []
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const value = useMemo(() => {
    const addItem = (product, quantity = 1) => {
      setItems((prev) => {
        const existing = prev.find((i) => i.product_id === product.id)
        if (existing) {
          return prev.map((i) =>
            i.product_id === product.id ? { ...i, quantity: i.quantity + quantity } : i,
          )
        }
        return [
          ...prev,
          {
            product_id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            quantity,
          },
        ]
      })
    }
    const removeItem = (productId) =>
      setItems((prev) => prev.filter((i) => i.product_id !== productId))
    const setQuantity = (productId, quantity) =>
      setItems((prev) =>
        quantity <= 0
          ? prev.filter((i) => i.product_id !== productId)
          : prev.map((i) => (i.product_id === productId ? { ...i, quantity } : i)),
      )
    const clear = () => setItems([])
    const count = items.reduce((sum, i) => sum + i.quantity, 0)
    const total = items.reduce((sum, i) => sum + i.price * i.quantity, 0)
    return { items, addItem, removeItem, setQuantity, clear, count, total }
  }, [items])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  return useContext(CartContext)
}
