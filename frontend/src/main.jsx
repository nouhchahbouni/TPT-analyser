import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import axios from 'axios'
import App from './App.jsx'
import './index.css'
import { installMockFallback } from './mockApi.js'

// Point axios to Railway backend if VITE_API_URL is set, otherwise same origin
const apiBase = import.meta.env.VITE_API_URL || ''
if (apiBase) {
  axios.defaults.baseURL = apiBase
}

// Fallback to mock data if API is unreachable
installMockFallback()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
