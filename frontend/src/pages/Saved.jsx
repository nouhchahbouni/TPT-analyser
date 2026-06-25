import React, { useEffect, useState } from 'react'
import axios from 'axios'
import MomentumBadge from '../components/MomentumBadge.jsx'
import OptimScore from '../components/OptimScore.jsx'

const fmt = n => typeof n === 'number' ? n.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'
const fmtRev = n => typeof n === 'number' ? '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'

export default function Saved() {
  const [saved, setSaved] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/saved')
      setSaved(res.data)
    } catch {
      setSaved([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const remove = async (id) => {
    await axios.delete(`/api/saved/${id}`)
    load()
  }

  if (loading) return <p style={{ color: '#1BA94C', fontWeight: 600 }}>Loading saved products...</p>

  if (!saved.length) return (
    <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
      <p style={{ fontSize: 48, marginBottom: 12 }}>⭐</p>
      <p style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>No saved products yet</p>
      <p style={{ fontSize: 15 }}>Save products from Search, Categories, or the Chrome Extension.</p>
    </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontWeight: 700, fontSize: 22 }}>⭐ Saved Products ({saved.length})</h2>
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        {saved.map(p => (
          <div key={p.id} style={{ background: '#fff', borderRadius: 12, border: '1px solid #E0E0E0', padding: 20, display: 'flex', gap: 20, alignItems: 'flex-start' }}>
            {p.thumbnail && (
              <img src={p.thumbnail} alt={p.title} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8, flexShrink: 0 }} />
            )}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <a href={p.url} target="_blank" rel="noreferrer"
                  style={{ fontWeight: 700, fontSize: 16, color: '#1BA94C', textDecoration: 'none' }}>
                  {p.title}
                </a>
                <button onClick={() => remove(p.id)}
                  style={{ background: 'none', border: 'none', color: '#E8463A', cursor: 'pointer', fontSize: 18 }}>×</button>
              </div>
              <p style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
                {p.shop_name} · {p.category} · ${p.price?.toFixed(2)}
              </p>
              <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                <div><p style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 2 }}>MONTHLY SALES</p><p style={{ fontWeight: 700 }}>{fmt(p.monthly_sales)}</p></div>
                <div><p style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 2 }}>TOTAL SALES</p><p style={{ fontWeight: 700 }}>{fmt(p.total_sales)}</p></div>
                <div><p style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 2 }}>MONTHLY REV</p><p style={{ fontWeight: 700, color: '#1BA94C' }}>{fmtRev(p.monthly_revenue)}</p></div>
                <div><p style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 2 }}>MOMENTUM</p><MomentumBadge label={p.momentum_label} /></div>
                <div><p style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 2 }}>OPTIM</p><OptimScore score={p.optimization_score} size={40} /></div>
              </div>
              {p.rating && (
                <p style={{ fontSize: 13, color: '#666', marginTop: 10 }}>
                  ⭐ {p.rating}/4.0 · {p.reviews_total} reviews · Saved {new Date(p.saved_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
