import React, { useEffect, useState, useMemo } from 'react'
import axios from 'axios'
import StatCard from '../components/StatCard.jsx'
import ProductTable from '../components/ProductTable.jsx'

const MOMENTUM_OPTS = [
  { value: '', label: 'Tous' },
  { value: 'exploding', label: '🔥 Exploding' },
  { value: 'growing', label: '📈 Growing' },
  { value: 'stable', label: '➡️ Stable' },
  { value: 'declining', label: '📉 Declining' },
]

const BADGE_OPTS = [
  { value: '', label: 'Tous' },
  { value: '👑 Dominant', label: '👑 Dominant' },
  { value: '✅ Solide', label: '✅ Solide' },
  { value: '⚠️ Moyen', label: '⚠️ Moyen' },
  { value: '🌱 Débutant', label: '🌱 Débutant' },
]

const GRADE_OPTS = [
  '', 'PreK', 'K', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th',
  '9th', '10th', '11th', '12th',
]

export default function Dashboard() {
  const [allProducts, setAllProducts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  // Filters
  const [filterCat, setFilterCat] = useState('')
  const [filterGrade, setFilterGrade] = useState('')
  const [filterMomentum, setFilterMomentum] = useState('')
  const [filterBadge, setFilterBadge] = useState('')
  const [priceMin, setPriceMin] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [minOpportunity, setMinOpportunity] = useState(0)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [prodRes, statRes] = await Promise.all([
          axios.get('/api/products', { params: { limit: 300 } }),
          axios.get('/api/stats'),
        ])
        setAllProducts(prodRes.data || [])
        setStats(statRes.data || null)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Unique categories from products
  const categories = useMemo(() => {
    const cats = [...new Set(allProducts.map(p => p.category).filter(Boolean))]
    return cats.sort()
  }, [allProducts])

  // Filtered + sorted products
  const displayed = useMemo(() => {
    return allProducts
      .filter(p => !filterCat || p.category === filterCat)
      .filter(p => !filterGrade || (p.grade_level || '').includes(filterGrade))
      .filter(p => !filterMomentum || p.indicators?.momentum?.status === filterMomentum)
      .filter(p => !filterBadge || (p.store?.badge || '') === filterBadge)
      .filter(p => !priceMin || p.price >= parseFloat(priceMin))
      .filter(p => !priceMax || p.price <= parseFloat(priceMax))
      .filter(p => (p.indicators?.final_opportunity_score ?? 0) >= minOpportunity)
      .sort((a, b) => (b.indicators?.final_opportunity_score ?? 0) - (a.indicators?.final_opportunity_score ?? 0))
      .slice(0, 300)
  }, [allProducts, filterCat, filterGrade, filterMomentum, filterBadge, priceMin, priceMax, minOpportunity])

  const statsData = stats ? [
    { label: 'Produits analysés', value: stats.total_products?.toLocaleString() || '0', icon: '📦', color: '#1BA94C' },
    { label: 'Trending 🔥', value: stats.trending_count || '0', icon: '🔥', color: '#E53935' },
    { label: 'Top revenue/mois', value: stats.top_revenue ? '$' + stats.top_revenue.toLocaleString() : '—', icon: '💰', color: '#FF8F00' },
    { label: 'Meilleure catégorie', value: stats.best_category || '—', icon: '🏆', color: '#7B1FA2' },
  ] : []

  const resetFilters = () => {
    setFilterCat(''); setFilterGrade(''); setFilterMomentum('')
    setFilterBadge(''); setPriceMin(''); setPriceMax(''); setMinOpportunity(0)
  }

  const hasFilters = filterCat || filterGrade || filterMomentum || filterBadge || priceMin || priceMax || minOpportunity > 0

  return (
    <div style={{ padding: '0 0 40px' }}>

      {/* Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1BA94C 0%, #0D7A35 100%)',
        borderRadius: 12, padding: '24px 32px', color: '#fff',
        marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
            🔥 Top produits TPT — Mis à jour ce matin
          </div>
          <div style={{ fontSize: 14, opacity: 0.85 }}>
            Classés par Score Opportunité · Données réelles TeachersPayTeachers
          </div>
        </div>
        <button
          onClick={() => axios.post('/api/scrape/enrich').then(() => window.location.reload())}
          style={{
            background: 'rgba(255,255,255,0.2)', color: '#fff', border: '1px solid rgba(255,255,255,0.4)',
            borderRadius: 8, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          ↻ Actualiser
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
          {statsData.map(s => <StatCard key={s.label} {...s} />)}
        </div>
      )}

      {/* Filtres */}
      <div style={{
        background: '#fff', border: '1px solid #E0E0E0', borderRadius: 10,
        padding: '14px 16px', marginBottom: 16,
        display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center',
      }}>
        {/* Catégorie */}
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
          style={{ fontSize: 12, padding: '5px 8px', borderRadius: 6, border: '1px solid #E0E0E0' }}>
          <option value="">Toutes catégories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        {/* Grade */}
        <select value={filterGrade} onChange={e => setFilterGrade(e.target.value)}
          style={{ fontSize: 12, padding: '5px 8px', borderRadius: 6, border: '1px solid #E0E0E0' }}>
          <option value="">Tous grades</option>
          {GRADE_OPTS.filter(Boolean).map(g => <option key={g} value={g}>{g}</option>)}
        </select>

        {/* Momentum */}
        <div style={{ display: 'flex', gap: 4 }}>
          {MOMENTUM_OPTS.map(o => (
            <button key={o.value} onClick={() => setFilterMomentum(o.value)}
              style={{
                padding: '4px 10px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
                border: `1px solid ${filterMomentum === o.value ? '#1BA94C' : '#E0E0E0'}`,
                background: filterMomentum === o.value ? '#E8F5E9' : '#fff',
                color: filterMomentum === o.value ? '#0D7A35' : '#555',
                fontWeight: filterMomentum === o.value ? 700 : 400,
              }}
            >{o.label}</button>
          ))}
        </div>

        {/* Prix min/max */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Prix</span>
          <input type="number" placeholder="Min" value={priceMin} onChange={e => setPriceMin(e.target.value)}
            style={{ width: 52, fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #E0E0E0' }} />
          <span style={{ fontSize: 12, color: '#999' }}>–</span>
          <input type="number" placeholder="Max" value={priceMax} onChange={e => setPriceMax(e.target.value)}
            style={{ width: 52, fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #E0E0E0' }} />
        </div>

        {/* Score opportunité min */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Opportunité ≥ {minOpportunity}</span>
          <input type="range" min={0} max={100} value={minOpportunity}
            onChange={e => setMinOpportunity(Number(e.target.value))}
            style={{ width: 80, accentColor: '#1BA94C' }} />
        </div>

        {/* Badge store */}
        <select value={filterBadge} onChange={e => setFilterBadge(e.target.value)}
          style={{ fontSize: 12, padding: '5px 8px', borderRadius: 6, border: '1px solid #E0E0E0' }}>
          {BADGE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>

        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#666' }}>
          {displayed.length} produits
        </span>

        {hasFilters && (
          <button onClick={resetFilters}
            style={{ fontSize: 11, color: '#E53935', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
            ✕ Reset
          </button>
        )}
      </div>

      {/* Tableau */}
      <ProductTable products={displayed} loading={loading} showSaveButton />
    </div>
  )
}
