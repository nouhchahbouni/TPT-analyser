import React, { useState } from 'react'
import axios from 'axios'
import ProductTable from '../components/ProductTable.jsx'
import MomentumBadge from '../components/MomentumBadge.jsx'

const PRELOADED = ['the-moffatt-girls','deanna-jump','rachel-lynette','fun-in-fifth-grade','lucky-little-learners','lindsay-bowden','appletastic-learning','the-stellar-teacher-company','science-and-math-doodles','math-in-the-middle']

export default function Stores() {
  const [query, setQuery] = useState('')
  const [storeData, setStoreData] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadStore = async (slug) => {
    setLoading(true)
    try {
      const res = await axios.get(`/api/stores?name=${slug}`)
      setStoreData(res.data)
    } catch {
      setStoreData(null)
    } finally {
      setLoading(false)
    }
  }

  const fmtRev = n => n >= 1000000 ? '$' + (n/1000000).toFixed(1) + 'M' : n >= 1000 ? '$' + (n/1000).toFixed(0) + 'K' : '$' + (n||0)

  return (
    <div>
      {/* Search */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', fontSize: 18 }}>🏪</span>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadStore(query.trim())}
            placeholder="Enter store name (e.g. the-moffatt-girls)..."
            style={{ width: '100%', padding: '14px 16px 14px 44px', borderRadius: 10, border: '2px solid #1BA94C', fontSize: 16, outline: 'none', fontFamily: 'Inter, sans-serif' }} />
        </div>
        <button onClick={() => loadStore(query.trim())}
          style={{ background: '#1BA94C', color: '#fff', border: 'none', borderRadius: 10, padding: '14px 28px', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>
          Analyze
        </button>
      </div>

      {/* Pre-loaded store chips */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontWeight: 600, fontSize: 13, color: '#666', marginBottom: 10 }}>Quick access:</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {PRELOADED.map(s => (
            <button key={s} onClick={() => { setQuery(s); loadStore(s); }}
              style={{ padding: '6px 14px', borderRadius: 20, border: '1px solid #1BA94C', background: '#fff', color: '#1BA94C', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading && <p style={{ color: '#1BA94C', fontWeight: 600 }}>Loading store data...</p>}

      {storeData && (
        <>
          {/* Store summary card */}
          <div style={{ background: 'linear-gradient(135deg, #1BA94C, #0D7A35)', borderRadius: 16, padding: 28, marginBottom: 24, color: '#fff' }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>🏪 {storeData.store_name}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
              {[
                { label: 'Total Revenue', value: fmtRev(storeData.total_revenue) },
                { label: 'Products', value: storeData.products?.length || 0 },
                { label: 'Avg Momentum', value: storeData.avg_momentum_label || '➡️' },
                { label: 'Best Sellers', value: storeData.best_sellers_count || 0 },
              ].map(item => (
                <div key={item.label} style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 10, padding: 16 }}>
                  <p style={{ opacity: 0.8, fontSize: 13, marginBottom: 4 }}>{item.label}</p>
                  <p style={{ fontSize: 22, fontWeight: 700 }}>{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Products table */}
          {storeData.products && <ProductTable products={storeData.products} showSaveButton />}
        </>
      )}

      {!loading && !storeData && (
        <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
          <p style={{ fontSize: 48, marginBottom: 12 }}>🏪</p>
          <p style={{ fontSize: 18 }}>Search a store or click a quick-access chip above</p>
        </div>
      )}
    </div>
  )
}
