import React, { useState, useEffect } from 'react'
import axios from 'axios'
import ProductTable from '../components/ProductTable.jsx'

export default function Top50() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get('/api/products?limit=50&sort=final_opportunity_score')
      .then(res => {
        const data = res.data || []
        // Sort by final_opportunity_score desc, fallback to opportunity_score
        const sorted = [...data].sort((a, b) => {
          const as = a.indicators?.final_opportunity_score ?? 0
          const bs = b.indicators?.final_opportunity_score ?? 0
          return bs - as
        })
        setProducts(sorted)
      })
      .catch(() => setProducts([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#2D2D2D', margin: 0 }}>
          🏆 Top 50 — Toutes catégories
        </h1>
        <p style={{ fontSize: 13, color: '#888', marginTop: 4 }}>
          Les 50 meilleurs produits par Opportunity Score, toutes catégories confondues
        </p>
      </div>
      <ProductTable products={products} loading={loading} />
    </div>
  )
}
