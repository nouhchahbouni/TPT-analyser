import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import axios from 'axios'

const navItems = [
  { path: '/dashboard', icon: '🏠', label: 'Dashboard' },
  { path: '/top50', icon: '🏆', label: 'Top 50' },
  { path: '/search', icon: '🔍', label: 'Search' },
  { path: '/stores', icon: '🏪', label: 'Stores' },
  { path: '/categories', icon: '📚', label: 'Categories' },
  { path: '/saved', icon: '⭐', label: 'Saved' },
]

const styles = {
  shell: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
    background: '#F5F5F5',
  },
  sidebar: {
    width: 220,
    minWidth: 220,
    background: '#FFFFFF',
    borderRight: '1px solid #E0E0E0',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 10,
  },
  logoBlock: {
    padding: '20px 16px',
    borderBottom: '1px solid #E0E0E0',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  logoSquare: {
    width: 40,
    height: 40,
    background: '#1BA94C',
    borderRadius: 8,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoTPT: {
    color: '#FFFFFF',
    fontWeight: 700,
    fontSize: 13,
    lineHeight: 1,
    letterSpacing: 0.5,
  },
  logoSub: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: 7,
    fontWeight: 600,
    lineHeight: 1,
    marginTop: 1,
  },
  logoText: {
    display: 'flex',
    flexDirection: 'column',
  },
  logoTitle: {
    fontWeight: 700,
    fontSize: 15,
    color: '#2D2D2D',
    lineHeight: 1,
  },
  logoTagline: {
    fontSize: 11,
    color: '#888',
    marginTop: 2,
  },
  nav: {
    flex: 1,
    padding: '12px 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    color: '#2D2D2D',
    textDecoration: 'none',
    transition: 'background 0.15s, color 0.15s',
  },
  navLinkActive: {
    background: '#E8F5E9',
    color: '#0D7A35',
    fontWeight: 600,
  },
  navIcon: {
    fontSize: 16,
    width: 20,
    textAlign: 'center',
  },
  sidebarFooter: {
    padding: '12px 16px',
    borderTop: '1px solid #E0E0E0',
    fontSize: 11,
    color: '#aaa',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    background: '#FFFFFF',
    borderBottom: '1px solid #E0E0E0',
    padding: '0 24px',
    height: 56,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 14,
    color: '#888',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  refreshBtn: {
    background: '#1BA94C',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: 8,
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  exportBtn: {
    background: 'transparent',
    color: '#1BA94C',
    border: '1.5px solid #1BA94C',
    borderRadius: 8,
    padding: '7px 14px',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: 24,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#1BA94C',
    display: 'inline-block',
    marginRight: 6,
  },
}

export default function Layout({ children }) {
  const navigate = useNavigate()
  const [refreshing, setRefreshing] = useState(false)
  const [toast, setToast] = useState(null)

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await axios.post('/api/scrape/keyword?q=math')
      setToast('Data refresh started! Results will update shortly.')
    } catch {
      setToast('Backend offline — showing cached data.')
    } finally {
      setRefreshing(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  const handleExport = () => {
    window.open('/api/export/csv', '_blank')
  }

  return (
    <div style={styles.shell}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.logoBlock}>
          <div style={styles.logoSquare}>
            <span style={styles.logoTPT}>TPT</span>
            <span style={styles.logoSub}>Analyzer</span>
          </div>
          <div style={styles.logoText}>
            <span style={styles.logoTitle}>TPT Analyzer</span>
            <span style={styles.logoTagline}>Market Intelligence</span>
          </div>
        </div>

        <nav style={styles.nav}>
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                ...styles.navLink,
                ...(isActive ? styles.navLinkActive : {}),
              })}
            >
              <span style={styles.navIcon}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}

          <div style={{ marginTop: 16, borderTop: '1px solid #E0E0E0', paddingTop: 16 }}>
            <NavLink
              to="/settings"
              style={styles.navLink}
              onClick={e => e.preventDefault()}
            >
              <span style={styles.navIcon}>⚙️</span>
              Settings
            </NavLink>
          </div>
        </nav>

        <div style={styles.sidebarFooter}>
          <span style={styles.statusDot}></span>
          API Connected
        </div>
      </aside>

      {/* Main area */}
      <div style={styles.main}>
        {/* Header */}
        <header style={styles.header}>
          <div style={styles.headerLeft}>
            <span>TPT Analyzer</span>
            <span>·</span>
            <span style={{ color: '#2D2D2D', fontWeight: 600 }}>Market Intelligence Platform</span>
          </div>
          <div style={styles.headerRight}>
            <button style={styles.exportBtn} onClick={handleExport}>
              ⬇ Export CSV
            </button>
            <button
              style={{ ...styles.refreshBtn, opacity: refreshing ? 0.7 : 1 }}
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? '⟳ Refreshing...' : '⟳ Refresh Data'}
            </button>
          </div>
        </header>

        {/* Toast */}
        {toast && (
          <div style={{
            position: 'fixed', top: 16, right: 16, zIndex: 999,
            background: '#1BA94C', color: '#fff',
            padding: '10px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
          }}>
            {toast}
          </div>
        )}

        {/* Page content */}
        <main style={styles.content}>
          {children}
        </main>
      </div>
    </div>
  )
}
