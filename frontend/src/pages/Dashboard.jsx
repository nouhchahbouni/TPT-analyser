import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import StatCard from '../components/StatCard.jsx'
import ProductTable from '../components/ProductTable.jsx'
import MomentumBadge from '../components/MomentumBadge.jsx'

const CATEGORY_ICONS = {
  'math': '📐', 'Math': '📐',
  'ela': '📖', 'ELA': '📖', 'Ela': '📖',
  'science': '🔬', 'Science': '🔬',
  'social studies': '🌍', 'Social Studies': '🌍',
  'sel': '💚', 'SEL': '💚',
  'back to school': '🎒', 'Back To School': '🎒',
  'teacher tools': '🛠️', 'Teacher Tools': '🛠️',
  'classroom decor': '🎨', 'Classroom Decor': '🎨',
  'special education': '⭐', 'Special Education': '⭐',
  'foreign language': '🌐', 'Foreign Language': '🌐',
}

function getCatIcon(cat) {
  if (!cat) return '📚'
  const key = Object.keys(CATEGORY_ICONS).find(k => cat.toLowerCase().includes(k.toLowerCase()))
  return key ? CATEGORY_ICONS[key] : '📚'
}

const styles = {
  banner: {
    background: 'linear-gradient(135deg, #1BA94C 0%, #0D7A35 100%)',
    borderRadius: 12,
    padding: '24px 32px',
    color: '#fff',
    marginBottom: 24,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bannerTitle: {
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 4,
  },
  bannerSub: {
    fontSize: 14,
    opacity: 0.85,
  },
  statGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16,
    marginBottom: 24,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: '#2D2D2D',
  },
  viewAll: {
    fontSize: 13,
    color: '#1BA94C',
    fontWeight: 600,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
  },
  catGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 12,
  },
  catCard: {
    background: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: 10,
    padding: '16px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  catIcon: {
    fontSize: 28,
    marginBottom: 6,
  },
  catName: {
    fontSize: 12,
    fontWeight: 600,
    color: '#2D2D2D',
    marginBottom: 4,
  },
  catCount: {
    fontSize: 11,
    color: '#888',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 16,
    marginBottom: 24,
  },
  oppRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 0',
    borderBottom: '1px solid #F0F0F0',
  },
  oppRank: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    background: '#1BA94C',
    color: '#fff',
    fontSize: 11,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  oppTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#2D2D2D',
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  card: {
    background: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: 12,
    padding: 16,
  },
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [trending, setTrending] = useState([])
  const [categories, setCategories] = useState([])
  const [opportunities, setOpportunities] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [statsRes, trendRes, catRes, prodRes] = await Promise.all([
          axios.get('/api/stats').catch(() => ({ data: {} })),
          axios.get('/api/trending?limit=10').catch(() => ({ data: { trending: [] } })),
          axios.get('/api/categories').catch(() => ({ data: { categories: [] } })),
          axios.get('/api/products?limit=50').catch(() => ({ data: { products: [] } })),
        ])
        setStats(statsRes.data)
        setTrending(trendRes.data.trending || [])
        setCategories((catRes.data.categories || []).slice(0, 10))
        // Opportunities: high optim score, lower momentum (hidden gems)
        const prods = prodRes.data.products || []
        const opps = [...prods]
          .filter(p => p.optim_score >= 60 && p.momentum < 15)
          .sort((a, b) => (b.optim_score - a.optim_score))
          .slice(0, 10)
        setOpportunities(opps)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

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
        <StatCard
          label="Products Analyzed"
          value={loading ? '…' : (stats?.total_products || 0).toLocaleString()}
          icon="📊"
          sub="In database"
          accent="#1BA94C"
        />
        <StatCard
          label="🔥 Trending Today"
          value={loading ? '…' : (stats?.trending_count || 0)}
          icon="🔥"
          sub="Momentum > 15%"
          accent="#E8463A"
        />
        <StatCard
          label="Top Revenue / Month"
          value={loading ? '…' : `$${(stats?.top_revenue || 0).toFixed(0)}`}
          icon="💰"
          sub="Single product"
          accent="#FF8F00"
          change="+12% vs last mo"
        />
        <StatCard
          label="Best Category"
          value={loading ? '…' : (stats?.best_category || 'Math')}
          icon="📚"
          sub={`Avg optim: ${stats?.avg_optim_score || 0}/100`}
          accent="#0D7A35"
        />
      </div>

      {/* Two column section */}
      <div style={styles.twoCol}>
        {/* Trending */}
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
                ${(p.monthly_revenue || 0).toFixed(0)}/mo
              </span>
            </div>
          ))}
        </div>

        {/* Opportunities */}
        <div style={styles.card}>
          <div style={styles.sectionHeader}>
            <span style={styles.sectionTitle}>Top Opportunities 💡</span>
            <button style={styles.viewAll} onClick={() => navigate('/search')}>View all →</button>
          </div>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 24 }}><span className="spinner"></span></div>
          ) : opportunities.length === 0 ? (
            <div style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>
              No opportunities found yet. Try searching for keywords.
            </div>
          ) : opportunities.map((p, i) => (
            <div key={p.id || i} style={styles.oppRow}>
              <div style={{ ...styles.oppRank, background: '#FF8F00' }}>{i + 1}</div>
              <div style={styles.oppTitle} title={p.title}>{p.title}</div>
              <span style={{ fontSize: 11, background: '#E8F5E9', color: '#0D7A35', padding: '2px 6px', borderRadius: 10, fontWeight: 600 }}>
                {p.optim_score}/100
              </span>
              <span style={{ fontSize: 11, color: '#888' }}>{p.category}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Category Grid */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionTitle}>Categories</span>
          <button style={styles.viewAll} onClick={() => navigate('/categories')}>View all →</button>
        </div>
        <div style={styles.catGrid}>
          {categories.map((cat, i) => (
            <div
              key={cat.category || i}
              style={styles.catCard}
              onClick={() => navigate(`/categories`)}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#1BA94C'
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(27,169,76,0.15)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#E0E0E0'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div style={styles.catIcon}>{getCatIcon(cat.category)}</div>
              <div style={styles.catName}>{cat.category}</div>
              <div style={styles.catCount}>{cat.product_count || 0} products</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
