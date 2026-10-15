import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import VoiceAgent from './components/VoiceAgent.jsx'
import Home from './pages/Home.jsx'
import Products from './pages/Products.jsx'
import Cart from './pages/Cart.jsx'
import Checkout from './pages/Checkout.jsx'
import OrderConfirmation from './pages/OrderConfirmation.jsx'
import Orders from './pages/Orders.jsx'

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/order-confirmation/:orderId" element={<OrderConfirmation />} />
          <Route path="/orders" element={<Orders />} />
        </Routes>
      </main>
      {/* Floating "Talk to Nova" voice assistant, available on every page */}
      <VoiceAgent />
    </div>
  )
}
