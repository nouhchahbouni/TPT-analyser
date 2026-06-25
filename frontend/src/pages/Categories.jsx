import React, { useEffect, useState } from 'react'
import axios from 'axios'
import ProductTable from '../components/ProductTable.jsx'

const CATEGORY_ICONS = {
  math: '📐', 'ela-english-language-arts': '📖', science: '🔬',
  'social-studies-history': '🌍', 'social-emotional-learning': '💚',
  'back-to-school': '🎒', 'teacher-tools': '🛠️', 'classroom-decor': '🎨',
  'special-education': '⭐', 'foreign-language': '🌐', health: '❤️', 'arts-music-drama': '🎭'
}

export default function Categories() {
  const [categories, setCategories] = useState([])
  const [selected, setSelected] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    axios.get('/api/categories').then(r => setCategories(r.data)).catch(() => {})
  }, [])

  const selectCategory = async (slug) => {
    setSelected(slug)
    setLoading(true)
    try {
      const res = await axios.get(`/api/category/${slug}/products`)
      setProducts(res.data)
    } catch {
      setProducts([])
    } finally {
      setLoading(false)
    }
  }

  const getMomentumColor = (label) => {
    if (label === '🔥') return '#E8463A'
    if (label === '📈') return '#1BA94C'
    if (label === '📉') return '#ff9800'
    return '#999'
  }

  return (
    <div>
      <h2 style={{ fontWeight: 700, fontSize: 22, marginBottom: 20 }}>📚 All Categories</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
        {categories.map(cat => (
          <div key={cat.slug} onClick={() => selectCategory(cat.slug)}
            style={{
              background: selected === cat.slug ? '#E8F5E9' : '#fff',
              border: selected === cat.slug ? '2px solid #1BA94C' : '1px solid #E0E0E0',
              borderRadius: 12, padding: 20, cursor: 'pointer',
              transition: 'all .2s', textAlign: 'center'
            }}>
            <p style={{ fontSize: 32, marginBottom: 8 }}>{CATEGORY_ICONS[cat.slug] || '📦'}</p>
            <p style={{ fontWeight: 700, fontSize: 14, marginBottom: 4, color: '#2D2D2D' }}>{cat.name}</p>
            <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{cat.product_count} products</p>
            <span style={{
              display: 'inline-block', padding: '2px 10px', borderRadius: 12,
              background: getMomentumColor(cat.avg_momentum) + '22',
              color: getMomentumColor(cat.avg_momentum), fontSize: 16, fontWeight: 600
            }}>{cat.avg_momentum || '➡️'}</span>
          </div>
        ))}
      </div>

      {loading && <p style={{ color: '#1BA94C', fontWeight: 600 }}>Loading products...</p>}

      {selected && !loading && products.length > 0 && (
        <>
          <h3 style={{ fontWeight: 700, fontSize: 18, marginBottom: 16 }}>
            {CATEGORY_ICONS[selected]} Top products in {selected.replace(/-/g, ' ')}
          </h3>
          <ProductTable products={products} showSaveButton />
        </>
      )}
    </div>
  )
}
