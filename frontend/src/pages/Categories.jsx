import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import { TPT_CATEGORIES, findCategoryById } from '../data/categories.js'
import ProductTable from '../components/ProductTable.jsx'

const SORT_OPTIONS = [
  { value: 'monthly_revenue', label: 'Monthly Revenue' },
  { value: 'total_revenue', label: 'Total Revenue' },
  { value: 'momentum', label: 'Momentum (Trending)' },
  { value: 'reviews_total', label: 'Most Reviews' },
  { value: 'optim_score', label: 'Optimization Score' },
  { value: 'price_asc', label: 'Price (Low → High)' },
  { value: 'price_desc', label: 'Price (High → Low)' },
]

const MOMENTUM_OPTIONS = [
  { value: '', label: 'All' },
  { value: '🔥', label: '🔥 Hot (>15%)' },
  { value: '📈', label: '📈 Rising (8-15%)' },
  { value: '➡️', label: '➡️ Stable (3-8%)' },
  { value: '📉', label: '📉 Declining (<3%)' },
]

// Recursive tree node
function TreeNode({ node, selectedId, onSelect, depth = 0 }) {
  const hasChildren = node.children && node.children.length > 0
  const isSelected = selectedId === node.id
  const isAncestor = hasChildren && node.children.some(c =>
    c.id === selectedId || (c.children && c.children.some(cc => cc.id === selectedId))
  )
  const [open, setOpen] = useState(isAncestor || depth === 0)

  useEffect(() => {
    if (isAncestor) setOpen(true)
  }, [isAncestor])

  const handleClick = () => {
    if (hasChildren) {
      setOpen(o => !o)
    }
    if (node.url) {
      onSelect(node)
    }
  }

  return (
    <div>
      <div
        onClick={handleClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: `5px ${8 + depth * 14}px`,
          borderRadius: 6,
          cursor: 'pointer',
          background: isSelected ? '#E8F5E9' : 'transparent',
          color: isSelected ? '#0D7A35' : '#2D2D2D',
          fontWeight: isSelected ? 700 : depth === 0 ? 600 : 400,
          fontSize: depth === 0 ? 13 : 12,
          transition: 'background 0.15s',
          userSelect: 'none',
        }}
        onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#F5F5F5' }}
        onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
      >
        {node.icon && depth === 0 && <span style={{ fontSize: 14 }}>{node.icon}</span>}
        {hasChildren && (
          <span style={{ fontSize: 10, color: '#999', minWidth: 10 }}>
            {open ? '▼' : '▶'}
          </span>
        )}
        {!hasChildren && <span style={{ minWidth: 10 }} />}
        <span style={{ flex: 1 }}>{node.name}</span>
      </div>

      {hasChildren && open && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.id}
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Categories() {
  const [selectedNode, setSelectedNode] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('monthly_revenue')
  const [momentum, setMomentum] = useState('')
  const [priceMin, setPriceMin] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [error, setError] = useState(null)

  const fetchProducts = useCallback(async (node) => {
    if (!node?.url) return
    setLoading(true)
    setError(null)
    setProducts([])
    try {
      const res = await axios.get('/api/products', {
        params: { category_url: node.url, limit: 50 }
      })
      setProducts(res.data || [])
    } catch (e) {
      setError('Failed to load products. Try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleSelect = (node) => {
    if (!node.url) return
    setSelectedNode(node)
    fetchProducts(node)
  }

  // Sort + filter products
  const displayed = [...products]
    .filter(p => !momentum || p.momentum_label === momentum)
    .filter(p => !priceMin || p.price >= parseFloat(priceMin))
    .filter(p => !priceMax || p.price <= parseFloat(priceMax))
    .sort((a, b) => {
      if (sortBy === 'price_asc') return a.price - b.price
      if (sortBy === 'price_desc') return b.price - a.price
      return (b[sortBy] || 0) - (a[sortBy] || 0)
    })

  return (
    <div style={{ display: 'flex', gap: 0, height: '100%', overflow: 'hidden' }}>

      {/* Left tree navigation */}
      <div style={{
        width: 240,
        minWidth: 240,
        borderRight: '1px solid #E0E0E0',
        overflowY: 'auto',
        padding: '12px 8px',
        background: '#FAFAFA',
      }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: 1, padding: '4px 8px', marginBottom: 8 }}>
          Categories
        </p>
        {TPT_CATEGORIES.map(cat => (
          <TreeNode
            key={cat.id}
            node={cat}
            selectedId={selectedNode?.id}
            onSelect={handleSelect}
            depth={0}
          />
        ))}
      </div>

      {/* Right content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>

        {/* Header */}
        {selectedNode ? (
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ fontWeight: 700, fontSize: 18, margin: 0 }}>
              {selectedNode.icon && <span style={{ marginRight: 6 }}>{selectedNode.icon}</span>}
              {selectedNode.name}
            </h2>
            <a
              href={`https://www.teacherspayteachers.com${selectedNode.url}`}
              target="_blank"
              rel="noreferrer"
              style={{ fontSize: 12, color: '#1BA94C', textDecoration: 'none' }}
            >
              View on TPT →
            </a>
          </div>
        ) : (
          <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>📂</p>
            <p style={{ fontSize: 16, fontWeight: 600 }}>Select a category</p>
            <p style={{ fontSize: 13 }}>Click any subcategory in the tree to see top products</p>
          </div>
        )}

        {/* Filters bar */}
        {selectedNode && (
          <div style={{
            display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center',
            background: '#fff', border: '1px solid #E0E0E0', borderRadius: 10,
            padding: '10px 14px', marginBottom: 16,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Sort by</span>
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #E0E0E0', cursor: 'pointer' }}
              >
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Momentum</span>
              <select
                value={momentum}
                onChange={e => setMomentum(e.target.value)}
                style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #E0E0E0', cursor: 'pointer' }}
              >
                {MOMENTUM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Price</span>
              <input
                type="number"
                placeholder="Min"
                value={priceMin}
                onChange={e => setPriceMin(e.target.value)}
                style={{ width: 56, fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #E0E0E0' }}
              />
              <span style={{ fontSize: 12, color: '#999' }}>–</span>
              <input
                type="number"
                placeholder="Max"
                value={priceMax}
                onChange={e => setPriceMax(e.target.value)}
                style={{ width: 56, fontSize: 12, padding: '4px 6px', borderRadius: 6, border: '1px solid #E0E0E0' }}
              />
            </div>

            <span style={{ marginLeft: 'auto', fontSize: 12, color: '#666' }}>
              {displayed.length} products
            </span>
          </div>
        )}

        {/* Content */}
        {loading && (
          <div style={{ textAlign: 'center', padding: 40, color: '#1BA94C', fontWeight: 600 }}>
            ⟳ Loading products from TPT...
          </div>
        )}

        {error && (
          <div style={{ background: '#FFF3F3', border: '1px solid #FFCDD2', borderRadius: 8, padding: 16, color: '#C62828', fontSize: 13 }}>
            {error}
          </div>
        )}

        {!loading && !error && selectedNode && displayed.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            <p>No products found. Try adjusting filters or refreshing data.</p>
          </div>
        )}

        {!loading && displayed.length > 0 && (
          <ProductTable products={displayed} showSaveButton />
        )}
      </div>
    </div>
  )
}
