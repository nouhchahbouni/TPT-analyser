import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import StatCard from '../components/StatCard.jsx'
import ProductTable from '../components/ProductTable.jsx'
import MomentumBadge from '../components/MomentumBadge.jsx'

const CATEGORY_ICONS = {
  'math': '📐', 'Math': '📐', 'ela': '📖', 'ELA': '📖',
  'science': '🔬', 'Science': '🔬', 'social studies': '🌍', 'Social Studies': '🌍',
  'sel': '💚', 'SEL': '💚', 'back to school': '🎒', 'Back To School': '🎒',
  'teacher tools': '🛠️', 'Teacher Tools': '🛠️', 'classroom decor': '🎨', 'Classroom Decor': '🎨',
  'special education': '⭐', 'Special Education': '⭐', 'foreign language': '🌐', 'Foreign Language': '🌐',
}

function getCatIcon(cat) {
  if (!cat) return '📚'
  const key = Object.keys(CATEGORY_ICONS).find(k => cat.toLowerCase().includes(k.toLowerCase()))
  return key ? CATEGORY_ICONS[key] : '📚'
}

const MOMENTUM_EMOJIS = ['🔥', '📈', '➡️', '📉']
const STORE_BADGES = ['👑 Dominant', '✅ Solide', '⚠️ Moyen', '🌱 Débutant']

const styles = {
  banner: {
    background: 'linear-gradient(135deg, #1BA94C 0%, #0D7A35 100%)',
    borderRadius: 12, padding: '24px 32px', color: '#fff',
    marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  bannerTitle: { fontSize: 22, fontWeight: 700, marginBottom: 4 },
  bannerSub: { fontSize: 14, opacity: 0.85 },
  statGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 },
  section: { marginBottom: 24 },
  sectionHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: 700, color: '#2D2D2D' },
  viewAll: { fontSize: 13, color: '#1BA94C', fontWeight: 600, cursor: 'pointer', background: 'none', border: 'none' },
  catGrid: { display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 },
  catCard: {
    background: '#FFFFFF', border: '1px solid #E0E0E0', borderRadius: 10,
    padding: '16px', textAlign: 'center', cursor: 'pointer', transition: 'all 0.2s',
  },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 },
  oppRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 0', borderBottom: '1px solid #F0F0F0',
  },
  oppRank: {
    width: 24, height: 24, borderRadius: '50%', background: '#1BA94C', color: '#fff',
    fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  oppTitle: { fontSize: 12, fontWeight: 600, color: '#2D2D2D', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  card: { background: '#FFFFFF', border: '1px solid #E0E0E0', borderRadius: 12, padding: 16 },
  filtersBar: {
    display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center',
    background: '#fff', border: '1px solid #E0E0E0', borderRadius: 10,
    padding: '10px 14px', marginBottom: 16,
  },
  filterLabel: { fontSize: 12, color: '#666', fontWeight: 600 },
  filterSelect: { fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #E0E0E0', cursor: 'pointer' },
  filterInput: { width: 60, fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #E0E0E0' },
  momBtn: (active) => ({
    fontSize: 16, padding: '2px 6px', borderRadius: 6, border: '1px solid',
    borderColor: active ? '#1BA94C' : '#E0E0E0', background: active ? '#E8F5E9' : '#fff',
    cursor: 'pointer',
  }),
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [trending, setTrending] = useState([])
  const [categories, setCategories] = useState([])
  const [allProducts, setAllProducts] = useState([])
  const [loading, setLoading] = useState(true)

  // Filters
  const [filterCat, setFilterCat] = useState('')
  const [filterMomentum, setFilterMomentum] = useState('')
  const [priceMin, setPriceMin] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [oppMin, setOppMin] = useState(0)
  const [filterBadge, setFilterBadge] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [statsRes, trendRes, catRes, prodRes] = await Promise.all([
          axios.get('/api/stats').catch(() => ({ data: {} })),
          axios.get('/api/trending?limit=10').catch(() => ({ data: [] })),
          axios.get('/api/categories').catch(() => ({ data: [] })),
          axios.get('/api/products?limit=300').catch(() => ({ data: [] })),
        ])
        setStats(statsRes.data)
        setTrending(Array.isArray(trendRes.data) ? trendRes.data : trendRes.data.trending || [])
        setCategories((Array.isArray(catRes.data) ? catRes.data : catRes.data.categories || []).slice(0, 10))
        const prods = Array.isArray(prodRes.data) ? prodRes.data : prodRes.data.products || []
        const sorted = [...prods].sort((a, b) => {
          const as = a.indicators?.final_opportunity_score ?? 0
          const bs = b.indicators?.final_opportunity_score ?? 0
          return bs - as
        })
        setAllProducts(sorted)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const uniqueCategories = useMemo(() => {
    const cats = new Set(allProducts.map(p => p.category).filter(Boolean))
    return Array.from(cats).sort()
  }, [allProducts])

  const filteredProducts = useMemo(() => {
    return allProducts
      .filter(p => !filterCat || p.category === filterCat)
      .filter(p => !filterMomentum || p.indicators?.momentum_emoji === filterMomentum)
      .filter(p => !priceMin || p.price >= parseFloat(priceMin))
      .filter(p => !priceMax || p.price <= parseFloat(priceMax))
      .filter(p => (p.indicators?.final_opportunity_score ?? 0) >= oppMin)
      .filter(p => !filterBadge || p.store_indicators?.badge === filterBadge)
  }, [allProducts, filterCat, filterMomentum, priceMin, priceMax, oppMin, filterBadge])

  const now = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })

  return (
    <div className="fade-in">
      {/* Banner */}
      <div style={styles.banner}>
        <div>
          <div style={styles.bannerTitle}>TPT Analyzer — What's Hot Right Now 🔥</div>
          <div style={styles.bannerSub}>Market intelligence updated {now}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 32, fontWeight: 700 }}>{stats?.total_products?.toLocaleString() || '—'}</div>
          <div style={{ fontSize: 12, opacity: 0.8 }}>Products Tracked</div>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={styles.statGrid}>
        <StatCard label="Products Analyzed" value={loading ? '…' : (stats?.total_products || 0).toLocaleString()} icon="📊" sub="In database" accent="#1BA94C" />
        <StatCard label="🔥 Trending Today" value={loading ? '…' : (stats?.trending_count || 0)} icon="🔥" sub="Momentum > 15%" accent="#E8463A" />
        <StatCard label="Top Revenue / Month" value={loading ? '…' : `$${(stats?.top_revenue || 0).toFixed(0)}`} icon="💰" sub="Single product" accent="#FF8F00" />
        <StatCard label="Best Category" value={loading ? '…' : (stats?.best_category || 'Math')} icon="📚" sub={`Avg optim: ${stats?.avg_optim_score || 0}/100`} accent="#0D7A35" />
      </div>

      {/* Top Products Section */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionTitle}>🔥 Top produits TPT — Mis à jour ce matin</span>
          <span style={{ fontSize: 12, color: '#888' }}>{filteredProducts.length} produits</span>
        </div>

        {/* Filters */}
        <div style={styles.filtersBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={styles.filterLabel}>Catégorie</span>
            <select value={filterCat} onChange={e => setFilterCat(e.target.value)} style={styles.filterSelect}>
              <option value="">All</option>
              {uniqueCategories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={styles.filterLabel}>Momentum</span>
            {MOMENTUM_EMOJIS.map(em => (
              <button key={em} style={styles.momBtn(filterMomentum === em)}
                onClick={() => setFilterMomentum(f => f === em ? '' : em)}>{em}</button>
            ))}
            {filterMomentum && <button onClick={() => setFilterMomentum('')} style={{ fontSize: 11, color: '#999', background: 'none', border: 'none', cursor: 'pointer' }}>All</button>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={styles.filterLabel}>Prix</span>
            <input type="number" placeholder="Min" value={priceMin} onChange={e => setPriceMin(e.target.value)} style={styles.filterInput} />
            <span style={{ fontSize: 12, color: '#999' }}>–</span>
            <input type="number" placeholder="Max" value={priceMax} onChange={e => setPriceMax(e.target.value)} style={styles.filterInput} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={styles.filterLabel}>Opp. min</span>
            <input type="range" min={0} max={100} value={oppMin} onChange={e => setOppMin(Number(e.target.value))} style={{ width: 80 }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: '#1BA94C' }}>{oppMin}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={styles.filterLabel}>Store badge</span>
            <select value={filterBadge} onChange={e => setFilterBadge(e.target.value)} style={styles.filterSelect}>
              <option value="">All</option>
              {STORE_BADGES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>

        <ProductTable products={filteredProducts} loading={loading} />
      </div>

      {/* Two column section */}
      <div style={styles.twoCol}>
        <div style={styles.card}>
          <div style={styles.sectionHeader}>
            <span style={styles.sectionTitle}>Exploding Right Now 🔥</span>
            <button style={styles.viewAll} onClick={() => navigate('/search')}>View all →</button>
          </div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 24 }}><span className="spinner"></span></div>
          ) : trending.length === 0 ? (
            <div style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>No trending products yet.</div>
          ) : trending.map((p, i) => (
            <div key={p.id || i} style={styles.oppRow}>
              <div style={styles.oppRank}>{i + 1}</div>
              <div style={styles.oppTitle} title={p.title}>{p.title}</div>
              <MomentumBadge label={p.momentum_label} momentum={p.momentum} />
              <span style={{ fontSize: 11, color: '#1BA94C', fontWeight: 600, whiteSpace: 'nowrap' }}>
                ${(p.monthly_revenue || p.indicators?.monthly_revenue || 0).toFixed(0)}/mo
              </span>
            </div>
          ))}
        </div>

        <div style={styles.card}>
          <div style={styles.sectionHeader}>
            <span style={styles.sectionTitle}>Categories</span>
            <button style={styles.viewAll} onClick={() => navigate('/categories')}>View all →</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            {categories.map((cat, i) => (
              <div key={cat.category || i} style={{ ...styles.catCard, padding: '10px' }}
                onClick={() => navigate('/categories')}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#1BA94C' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E0E0E0' }}
              >
                <div style={{ fontSize: 20, marginBottom: 4 }}>{getCatIcon(cat.category)}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#2D2D2D' }}>{cat.category}</div>
                <div style={{ fontSize: 10, color: '#888' }}>{cat.product_count || 0} products</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
