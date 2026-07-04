import React, { useState } from 'react'
import axios from 'axios'

const fmt = n => typeof n === 'number' ? n.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'

function parseCategoryPath(categoryUrl) {
  if (!categoryUrl) return null
  const parts = categoryUrl.replace(/^\/browse\//, '').split('/').filter(Boolean)
  return parts.map(p => p.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())).join(' › ')
}
const fmtRev = n => typeof n === 'number' ? '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'
const fmtPrice = n => typeof n === 'number' ? '$' + n.toFixed(2) : '—'

function ScoreCircle({ score, size = 40 }) {
  const s = typeof score === 'number' ? score : 0
  const bg = s >= 70 ? '#1BA94C' : s >= 40 ? '#FF8F00' : '#E8463A'
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: bg, color: '#fff', fontSize: size > 36 ? 12 : 10,
      fontWeight: 700, display: 'flex', alignItems: 'center',
      justifyContent: 'center', flexShrink: 0,
    }}>
      {Math.round(s)}
    </div>
  )
}

function MomentumBadge({ momentum }) {
  if (!momentum) return <span style={{ color: '#999' }}>—</span>
  const { emoji, status, score } = momentum
  if (status === 'no_data') return (
    <span style={{ fontSize: 11, color: '#999' }}>⏳ Après 24h</span>
  )
  const colors = { exploding: '#E8463A', growing: '#1BA94C', stable: '#FF8F00', declining: '#999' }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 16 }}>{emoji}</span>
      <span style={{ fontSize: 10, color: colors[status] || '#999', fontWeight: 600 }}>
        {score != null ? score.toFixed(1) + '%' : ''}
      </span>
    </div>
  )
}

function QualityBadge({ score, maxScore, partial }) {
  if (score == null) return <span style={{ color: '#999' }}>—</span>
  const s = typeof score === 'number' ? score : 0
  const bg = s >= 70 ? '#1BA94C' : s >= 40 ? '#FF8F00' : '#E8463A'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <div style={{
        width: 40, height: 40, borderRadius: '50%',
        background: bg, color: '#fff', fontSize: 10,
        fontWeight: 700, display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexShrink: 0,
      }}>
        {Math.round(s)}
      </div>
      {partial && <span style={{ fontSize: 9, color: '#FF8F00' }}>⚠️ partiel</span>}
    </div>
  )
}

const columns = [
  { key: 'thumbnail', label: '', width: 66, nosort: true },
  { key: 'title', label: 'Title', width: 220 },
  { key: 'store', label: 'Store', width: 140 },
  { key: 'price', label: 'Price', width: 80 },
  { key: 'reviews', label: 'Reviews', width: 90 },
  { key: 'favorites', label: 'Favoris', width: 80 },
  { key: 'total_sales', label: 'Ventes totales', width: 100 },
  { key: 'monthly_revenue', label: 'Rev/mo', width: 90 },
  { key: 'downloads', label: 'Downloads', width: 90 },
  { key: 'momentum', label: 'Momentum', width: 100 },
  { key: 'quality_score', label: 'Quality', width: 70 },
  { key: 'final_opportunity_score', label: 'Opportunity', width: 90 },
]

const styles = {
  wrapper: { background: '#FFFFFF', border: '1px solid #E0E0E0', borderRadius: 12, overflow: 'hidden' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: {
    padding: '10px 12px', textAlign: 'left', fontWeight: 600, fontSize: 12, color: '#666',
    background: '#FAFAFA', borderBottom: '1px solid #E0E0E0', whiteSpace: 'nowrap',
    cursor: 'pointer', userSelect: 'none',
  },
  td: { padding: '10px 12px', borderBottom: '1px solid #F0F0F0', verticalAlign: 'middle' },
  thumbnail: { width: 60, height: 45, objectFit: 'cover', borderRadius: 4, background: '#E8F5E9' },
  titleLink: {
    color: '#2D2D2D', fontWeight: 600, fontSize: 12,
    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
    overflow: 'hidden', maxWidth: 200, lineHeight: 1.3, textDecoration: 'none',
  },
  shopName: { fontSize: 11, color: '#1BA94C', fontWeight: 600 },
  storeBadge: {
    display: 'inline-block', fontSize: 10, padding: '1px 5px', borderRadius: 4,
    background: '#F5F5F5', color: '#666', fontWeight: 600, marginTop: 2,
  },
  emptyRow: { textAlign: 'center', padding: '40px 0', color: '#888', fontSize: 14 },
  sortIcon: { marginLeft: 4, opacity: 0.5 },
  bsBadge: {
    display: 'inline-block', background: '#FFF8E1', color: '#FF8F00',
    fontSize: 10, fontWeight: 600, borderRadius: 4, padding: '1px 5px', marginTop: 2,
  },
}

function getSortValue(p, key) {
  if (key === 'total_sales') return p.indicators?.total_sales ?? 0
  if (key === 'monthly_revenue') return p.indicators?.monthly_revenue ?? p.monthly_revenue ?? 0
  if (key === 'momentum') return p.indicators?.momentum_score ?? p.momentum ?? 0
  if (key === 'quality_score') return p.indicators?.quality_score ?? p.optim_score ?? 0
  if (key === 'final_opportunity_score') return p.indicators?.final_opportunity_score ?? 0
  if (key === 'downloads') return p.downloads ?? 0
  if (key === 'favorites') return p.favorites ?? p.favoris ?? 0
  if (key === 'reviews') return p.reviews_total ?? 0
  if (key === 'store') return p.store?.name ?? p.shop_name ?? ''
  return p[key] ?? 0
}

export default function ProductTable({ products = [], loading = false, compact = false }) {
  const [sortKey, setSortKey] = useState('final_opportunity_score')
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
    const av = getSortValue(a, sortKey)
    const bv = getSortValue(b, sortKey)
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
    } catch {}
    setSaved(s => ({ ...s, [product.id]: true }))
  }

  const visibleCols = compact
    ? columns.filter(c => ['thumbnail', 'title', 'monthly_revenue', 'momentum', 'final_opportunity_score'].includes(c.key))
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
                  {!col.nosort && sortKey === col.key && <span style={styles.sortIcon}>{sortDir === 'asc' ? '↑' : '↓'}</span>}
                  {!col.nosort && sortKey !== col.key && <span style={styles.sortIcon}>↕</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={visibleCols.length} style={styles.emptyRow}>Loading products...</td></tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr><td colSpan={visibleCols.length} style={styles.emptyRow}>No products found.</td></tr>
            )}
            {!loading && sorted.map((p, i) => {
              const ind = p.indicators || {}
              const storeInd = p.store_indicators || {}
              const store = p.store || {}
              const monthlyRev = ind.monthly_revenue ?? p.monthly_revenue ?? 0
              const revColor = monthlyRev >= 500 ? '#1BA94C' : monthlyRev >= 100 ? '#FF8F00' : '#E8463A'
              const favorites = p.favorites ?? p.favoris ?? 0
              const totalSales = ind.total_sales ?? 0
              const qualityScore = ind.quality_score ?? p.optim_score ?? 0
              const qualityMax = ind.quality_max_score ?? 100
              const qualityPartial = ind.quality_partial ?? false
              const finalScore = ind.final_opportunity_score ?? null
              const momentumData = ind.momentum_score !== undefined ? {
                emoji: ind.momentum_emoji || '➡️',
                status: ind.momentum_status || 'stable',
                score: ind.momentum_score,
              } : null

              return (
                <tr
                  key={p.id || p.url || i}
                  style={{ background: i % 2 === 0 ? '#FFFFFF' : '#FAFAFA' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#F0FAF3'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#FFFFFF' : '#FAFAFA'}
                >
                  {visibleCols.map(col => (
                    <td key={col.key} style={styles.td}>
                      {col.key === 'thumbnail' && (
                        <a href={p.url} target="_blank" rel="noreferrer">
                          <img
                            src={p.thumbnail || `https://picsum.photos/seed/${p.id || i}/60/45`}
                            alt=""
                            style={styles.thumbnail}
                            onError={e2 => { e2.target.src = `https://picsum.photos/seed/${i + 100}/60/45` }}
                          />
                        </a>
                      )}
                      {col.key === 'title' && (
                        <div>
                          <a href={p.url} target="_blank" rel="noreferrer" style={styles.titleLink} title={p.title}>
                            {p.title ? (p.title.length > 60 ? p.title.slice(0, 60) + '…' : p.title) : '—'}
                          </a>
                          {parseCategoryPath(p.category_url) && (
                            <div style={{ fontSize: 10, color: '#888', marginTop: 3, lineHeight: 1.4 }}>
                              📂 {parseCategoryPath(p.category_url)}
                            </div>
                          )}
                          {p.has_bestseller && <div style={styles.bsBadge}>🏆 Best Seller</div>}
                        </div>
                      )}
                      {col.key === 'store' && (
                        <div>
                          <a href={p.shop_url || store.shop_url} target="_blank" rel="noreferrer" style={styles.shopName}>
                            {store.name || p.shop_name || '—'}
                          </a>
                          {storeInd.badge && (
                            <div style={storeInd.badge.startsWith('⏳') ? { fontSize: 10, color: '#999', marginTop: 2 } : styles.storeBadge}>
                              {storeInd.badge}
                            </div>
                          )}
                        </div>
                      )}
                      {col.key === 'price' && (
                        p.original_price && p.original_price > p.price ? (
                          <div>
                            <div style={{ textDecoration: 'line-through', color: '#999', fontSize: 11 }}>
                              {fmtPrice(p.original_price)}
                            </div>
                            <div style={{ color: '#E8463A', fontWeight: 700 }}>
                              {fmtPrice(p.price)}
                            </div>
                          </div>
                        ) : fmtPrice(p.price)
                      )}
                      {col.key === 'reviews' && (
                        <div>
                          <div style={{ fontWeight: 600 }}>{fmt(p.reviews_total)}</div>
                          {p.rating > 0 && <div style={{ fontSize: 11, color: '#FF8F00' }}>⭐ {p.rating.toFixed(1)}</div>}
                        </div>
                      )}
                      {col.key === 'favorites' && (
                        <span style={{ color: '#E8463A' }}>❤️ {fmt(favorites)}</span>
                      )}
                      {col.key === 'total_sales' && (
                        <span style={{ fontWeight: 600 }}>{fmt(totalSales)}</span>
                      )}
                      {col.key === 'monthly_revenue' && (
                        monthlyRev != null
                          ? <span style={{ color: revColor, fontWeight: 600 }}>{fmtRev(monthlyRev)}</span>
                          : <span style={{ fontSize: 10, color: '#999' }}>⏳ Date manquante</span>
                      )}
                      {col.key === 'downloads' && (
                        <span style={{ fontWeight: 600 }}>{fmt(p.downloads ?? null)}</span>
                      )}
                      {col.key === 'momentum' && <MomentumBadge momentum={momentumData} />}
                      {col.key === 'quality_score' && (
                        <QualityBadge score={qualityScore} maxScore={qualityMax} partial={qualityPartial} />
                      )}
                      {col.key === 'final_opportunity_score' && (
                        finalScore != null
                          ? <ScoreCircle score={finalScore} size={44} />
                          : <span style={{ fontSize: 10, color: '#999' }}>⏳</span>
                      )}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
