import React, { useState } from 'react'
import MomentumBadge from './MomentumBadge.jsx'
import OptimScore from './OptimScore.jsx'
import axios from 'axios'

const fmt = n => typeof n === 'number' ? n.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'
const fmtRev = n => typeof n === 'number' ? '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'
const fmtPrice = n => typeof n === 'number' ? '$' + n.toFixed(2) : '—'

const columns = [
  { key: 'thumbnail', label: '', width: 56, nosort: true },
  { key: 'title', label: 'Title', width: 220 },
  { key: 'monthly_sales', label: 'Mo. Sales', width: 90 },
  { key: 'total_sales', label: 'Total Sales', width: 90 },
  { key: 'momentum_label', label: 'Trend', width: 80, nosort: true },
  { key: 'monthly_revenue', label: 'Mo. Revenue', width: 110 },
  { key: 'total_revenue', label: 'Total Revenue', width: 110 },
  { key: 'optim_score', label: 'Optim', width: 60 },
  { key: 'price', label: 'Price', width: 70 },
  { key: 'category', label: 'Category', width: 100 },
  { key: 'shop_name', label: 'Shop', width: 130 },
  { key: 'rating', label: 'Rating', width: 70 },
  { key: 'save', label: '', width: 70, nosort: true },
]

const styles = {
  wrapper: {
    background: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: 12,
    overflow: 'hidden',
  },
  tableWrap: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    padding: '10px 12px',
    textAlign: 'left',
    fontWeight: 600,
    fontSize: 12,
    color: '#666',
    background: '#FAFAFA',
    borderBottom: '1px solid #E0E0E0',
    whiteSpace: 'nowrap',
    cursor: 'pointer',
    userSelect: 'none',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #F0F0F0',
    verticalAlign: 'middle',
  },
  thumbnail: {
    width: 44,
    height: 33,
    objectFit: 'cover',
    borderRadius: 4,
    background: '#E8F5E9',
  },
  titleLink: {
    color: '#2D2D2D',
    fontWeight: 600,
    fontSize: 12,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
    maxWidth: 200,
    lineHeight: 1.3,
  },
  shopName: {
    fontSize: 11,
    color: '#1BA94C',
    fontWeight: 600,
  },
  saveBtn: {
    background: '#1BA94C',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '5px 10px',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
  },
  savedBtn: {
    background: '#E8F5E9',
    color: '#0D7A35',
    border: '1px solid #1BA94C',
    borderRadius: 6,
    padding: '5px 10px',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'default',
  },
  starRating: {
    color: '#FF8F00',
    fontSize: 12,
  },
  bsBadge: {
    display: 'inline-block',
    background: '#FFF8E1',
    color: '#FF8F00',
    fontSize: 10,
    fontWeight: 600,
    borderRadius: 4,
    padding: '1px 5px',
    marginTop: 2,
  },
  emptyRow: {
    textAlign: 'center',
    padding: '40px 0',
    color: '#888',
    fontSize: 14,
  },
  sortIcon: {
    marginLeft: 4,
    opacity: 0.5,
  },
}

export default function ProductTable({ products = [], loading = false, compact = false }) {
  const [sortKey, setSortKey] = useState('momentum')
  const [sortDir, setSortDir] = useState('desc')
  const [saved, setSaved] = useState({})

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = [...products].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (av === undefined || bv === undefined) return 0
    if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortDir === 'asc' ? av - bv : bv - av
  })

  const handleSave = async (product) => {
    if (saved[product.id]) return
    try {
      await axios.post('/api/saved', {
        product_id: product.id || 0,
        url: product.url || '',
        title: product.title || '',
        notes: '',
      })
      setSaved(s => ({ ...s, [product.id]: true }))
    } catch {
      setSaved(s => ({ ...s, [product.id]: true }))
    }
  }

  const visibleCols = compact
    ? columns.filter(c => ['thumbnail', 'title', 'monthly_revenue', 'momentum_label', 'optim_score', 'save'].includes(c.key))
    : columns

  return (
    <div style={styles.wrapper}>
      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              {visibleCols.map(col => (
                <th
                  key={col.key}
                  style={{ ...styles.th, width: col.width, minWidth: col.width }}
                  onClick={() => !col.nosort && handleSort(col.key)}
                >
                  {col.label}
                  {!col.nosort && sortKey === col.key && (
                    <span style={styles.sortIcon}>{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                  {!col.nosort && sortKey !== col.key && <span style={styles.sortIcon}>↕</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={visibleCols.length} style={styles.emptyRow}>
                  <span className="spinner" style={{ margin: '0 auto', display: 'block' }}></span>
                  <div style={{ marginTop: 8 }}>Loading products...</div>
                </td>
              </tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={visibleCols.length} style={styles.emptyRow}>
                  No products found.
                </td>
              </tr>
            )}
            {!loading && sorted.map((p, i) => (
              <tr
                key={p.id || p.url || i}
                style={{ background: i % 2 === 0 ? '#FFFFFF' : '#FAFAFA' }}
                onMouseEnter={e => e.currentTarget.style.background = '#F0FAF3'}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#FFFFFF' : '#FAFAFA'}
              >
                {visibleCols.map(col => (
                  <td key={col.key} style={styles.td}>
                    {col.key === 'thumbnail' && (
                      <img
                        src={p.thumbnail || `https://picsum.photos/seed/${p.id || i}/44/33`}
                        alt=""
                        style={styles.thumbnail}
                        onError={e => { e.target.src = `https://picsum.photos/seed/${i + 100}/44/33` }}
                      />
                    )}
                    {col.key === 'title' && (
                      <div>
                        <a
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                          style={styles.titleLink}
                          title={p.title}
                        >
                          {p.title}
                        </a>
                        {p.has_bestseller && <div style={styles.bsBadge}>🏆 Best Seller</div>}
                      </div>
                    )}
                    {col.key === 'monthly_sales' && fmt(p.monthly_sales)}
                    {col.key === 'total_sales' && fmt(p.total_sales)}
                    {col.key === 'momentum_label' && (
                      <MomentumBadge label={p.momentum_label} momentum={p.momentum} />
                    )}
                    {col.key === 'monthly_revenue' && (
                      <span style={{ color: '#1BA94C', fontWeight: 600 }}>
                        {fmtRev(p.monthly_revenue)}
                      </span>
                    )}
                    {col.key === 'total_revenue' && fmtRev(p.total_revenue)}
                    {col.key === 'optim_score' && <OptimScore score={p.optim_score} />}
                    {col.key === 'price' && fmtPrice(p.price)}
                    {col.key === 'category' && (
                      <span style={{ fontSize: 11, background: '#F5F5F5', padding: '2px 6px', borderRadius: 4 }}>
                        {p.category}
                      </span>
                    )}
                    {col.key === 'shop_name' && (
                      <a
                        href={p.shop_url}
                        target="_blank"
                        rel="noreferrer"
                        style={styles.shopName}
                      >
                        {p.shop_name || '—'}
                      </a>
                    )}
                    {col.key === 'rating' && (
                      <span style={styles.starRating}>
                        ★ {p.rating ? p.rating.toFixed(1) : '—'}
                      </span>
                    )}
                    {col.key === 'save' && (
                      <button
                        style={saved[p.id] ? styles.savedBtn : styles.saveBtn}
                        onClick={() => handleSave(p)}
                        disabled={saved[p.id]}
                      >
                        {saved[p.id] ? '✓ Saved' : '+ Save'}
                      </button>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
