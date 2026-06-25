import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import ProductTable from '../components/ProductTable.jsx'

const CATEGORIES = ['Math', 'ELA', 'Science', 'Social Studies', 'SEL', 'Back to School', 'Teacher Tools', 'Classroom Decor', 'Special Education', 'Foreign Language']
const GRADES = ['PreK', 'K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
const MOMENTUM_OPTS = [
  { label: '🔥 Hot (>15%)', value: 'hot', min: 15 },
  { label: '📈 Rising (8-15%)', value: 'rising', min: 8, max: 15 },
  { label: '➡️ Stable (3-8%)', value: 'stable', min: 3, max: 8 },
  { label: '📉 Declining (<3%)', value: 'declining', max: 3 },
]

const styles = {
  page: { display: 'flex', gap: 20 },
  filters: {
    width: 220,
    minWidth: 220,
    background: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: 12,
    padding: 16,
    alignSelf: 'flex-start',
    position: 'sticky',
    top: 0,
  },
  filterTitle: { fontSize: 13, fontWeight: 700, color: '#2D2D2D', marginBottom: 12 },
  filterSection: { marginBottom: 16 },
  filterLabel: { fontSize: 11, fontWeight: 600, color: '#666', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  checkRow: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, cursor: 'pointer', fontSize: 12 },
  main: { flex: 1, display: 'flex', flexDirection: 'column', gap: 16 },
  searchBar: {
    display: 'flex',
    gap: 10,
    background: '#FFFFFF',
    border: '2px solid #1BA94C',
    borderRadius: 12,
    padding: '10px 16px',
    alignItems: 'center',
  },
  searchInput: {
    flex: 1,
    border: 'none',
    outline: 'none',
    fontSize: 15,
    color: '#2D2D2D',
    background: 'transparent',
  },
  searchBtn: {
    background: '#1BA94C',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '8px 20px',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  resultsMeta: {
    fontSize: 13,
    color: '#666',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  scrapeBtn: {
    background: 'transparent',
    border: '1px solid #1BA94C',
    color: '#1BA94C',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  },
  rangeRow: { display: 'flex', gap: 6, alignItems: 'center', fontSize: 11 },
  rangeInput: { flex: 1, accentColor: '#1BA94C' },
  toggleBtn: {
    padding: '4px 10px',
    borderRadius: 6,
    border: '1px solid #E0E0E0',
    background: '#F5F5F5',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    marginBottom: 4,
    width: '100%',
    textAlign: 'left',
  },
  toggleBtnActive: {
    background: '#E8F5E9',
    borderColor: '#1BA94C',
    color: '#0D7A35',
  },
  momentumBtn: {
    padding: '4px 8px',
    borderRadius: 6,
    border: '1px solid #E0E0E0',
    background: '#F5F5F5',
    fontSize: 11,
    cursor: 'pointer',
    marginBottom: 3,
    width: '100%',
    textAlign: 'left',
  },
  momentumBtnActive: {
    background: '#E8F5E9',
    borderColor: '#1BA94C',
    color: '#0D7A35',
    fontWeight: 600,
  },
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [inputVal, setInputVal] = useState('')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [scraping, setScraping] = useState(false)

  // Filters
  const [selCats, setSelCats] = useState([])
  const [priceMin, setPriceMin] = useState(0)
  const [priceMax, setPriceMax] = useState(50)
  const [minOptim, setMinOptim] = useState(0)
  const [selMomentum, setSelMomentum] = useState(null)
  const [bestSellerOnly, setBestSellerOnly] = useState(false)

  const fetchProducts = useCallback(async (q) => {
    setLoading(true)
    try {
      const res = await axios.get('/api/products', {
        params: { q, limit: 100 }
      })
      let prods = res.data.products || []

      // Apply client-side filters
      if (selCats.length > 0) {
        prods = prods.filter(p => selCats.some(c => p.category?.toLowerCase().includes(c.toLowerCase())))
      }
      prods = prods.filter(p => (p.price || 0) >= priceMin && (p.price || 0) <= priceMax)
      prods = prods.filter(p => (p.optim_score || 0) >= minOptim)
      if (bestSellerOnly) prods = prods.filter(p => p.has_bestseller)
      if (selMomentum) {
        const opt = MOMENTUM_OPTS.find(o => o.value === selMomentum)
        if (opt) {
          prods = prods.filter(p => {
            const m = p.momentum || 0
            if (opt.min !== undefined && m < opt.min) return false
            if (opt.max !== undefined && m >= opt.max) return false
            return true
          })
        }
      }

      setProducts(prods)
      setTotal(prods.length)
    } catch {
      setProducts([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [selCats, priceMin, priceMax, minOptim, selMomentum, bestSellerOnly])

  useEffect(() => {
    fetchProducts(query)
  }, [query, selCats, priceMin, priceMax, minOptim, selMomentum, bestSellerOnly])

  const handleSearch = () => {
    setQuery(inputVal)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handleScrape = async () => {
    if (!query) return
    setScraping(true)
    try {
      await axios.post(`/api/scrape/keyword?q=${encodeURIComponent(query)}`)
      setTimeout(() => fetchProducts(query), 3000)
    } finally {
      setScraping(false)
    }
  }

  const toggleCat = (cat) => {
    setSelCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])
  }

  return (
    <div style={styles.page} className="fade-in">
      {/* Filters Panel */}
      <aside style={styles.filters}>
        <div style={styles.filterTitle}>🔧 Filters</div>

        <div style={styles.filterSection}>
          <div style={styles.filterLabel}>Category</div>
          {CATEGORIES.map(cat => (
            <label key={cat} style={styles.checkRow}>
              <input
                type="checkbox"
                checked={selCats.includes(cat)}
                onChange={() => toggleCat(cat)}
                style={{ accentColor: '#1BA94C' }}
              />
              {cat}
            </label>
          ))}
        </div>

        <div style={styles.filterSection}>
          <div style={styles.filterLabel}>Price Range</div>
          <div style={styles.rangeRow}>
            <span>${priceMin}</span>
            <input type="range" min={0} max={50} value={priceMin}
              onChange={e => setPriceMin(+e.target.value)} style={styles.rangeInput} />
          </div>
          <div style={styles.rangeRow}>
            <span>${priceMax}</span>
            <input type="range" min={0} max={50} value={priceMax}
              onChange={e => setPriceMax(+e.target.value)} style={styles.rangeInput} />
          </div>
          <div style={{ fontSize: 11, color: '#888' }}>
            ${priceMin} – ${priceMax}
          </div>
        </div>

        <div style={styles.filterSection}>
          <div style={styles.filterLabel}>Momentum</div>
          {MOMENTUM_OPTS.map(opt => (
            <button
              key={opt.value}
              style={selMomentum === opt.value ? { ...styles.momentumBtn, ...styles.momentumBtnActive } : styles.momentumBtn}
              onClick={() => setSelMomentum(s => s === opt.value ? null : opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div style={styles.filterSection}>
          <div style={styles.filterLabel}>Optim Score ≥ {minOptim}</div>
          <input type="range" min={0} max={100} value={minOptim}
            onChange={e => setMinOptim(+e.target.value)} style={{ width: '100%', accentColor: '#1BA94C' }} />
        </div>

        <div style={styles.filterSection}>
          <div style={styles.filterLabel}>Best Seller</div>
          <button
            style={bestSellerOnly ? { ...styles.toggleBtn, ...styles.toggleBtnActive } : styles.toggleBtn}
            onClick={() => setBestSellerOnly(b => !b)}
          >
            {bestSellerOnly ? '✓ Best Sellers Only' : 'All Products'}
          </button>
        </div>

        <button
          style={{ ...styles.searchBtn, width: '100%', padding: '8px 0', marginTop: 4 }}
          onClick={() => { setSelCats([]); setPriceMin(0); setPriceMax(50); setMinOptim(0); setSelMomentum(null); setBestSellerOnly(false) }}
        >
          Reset Filters
        </button>
      </aside>

      {/* Main Search Area */}
      <div style={styles.main}>
        <div style={styles.searchBar}>
          <span style={{ fontSize: 18 }}>🔍</span>
          <input
            style={styles.searchInput}
            placeholder="Search TPT keywords... (e.g. math centers, phonics worksheets)"
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button style={styles.searchBtn} onClick={handleSearch}>
            Search
          </button>
        </div>

        <div style={styles.resultsMeta}>
          <span>{total} products found{query ? ` for "${query}"` : ''}</span>
          {query && (
            <button style={styles.scrapeBtn} onClick={handleScrape} disabled={scraping}>
              {scraping ? '⟳ Scraping...' : '🔄 Scrape Fresh Data'}
            </button>
          )}
          {loading && <span className="spinner" style={{ width: 14, height: 14 }}></span>}
        </div>

        <ProductTable products={products} loading={loading} />
      </div>
    </div>
  )
}
