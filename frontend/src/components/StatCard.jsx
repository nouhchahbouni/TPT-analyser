import React from 'react'

const styles = {
  card: {
    background: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: 12,
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    transition: 'box-shadow 0.2s',
    cursor: 'default',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  label: {
    fontSize: 13,
    color: '#666',
    fontWeight: 600,
  },
  icon: {
    fontSize: 20,
    background: '#E8F5E9',
    borderRadius: 8,
    width: 36,
    height: 36,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  value: {
    fontSize: 28,
    fontWeight: 700,
    color: '#2D2D2D',
    lineHeight: 1,
  },
  sub: {
    fontSize: 12,
    color: '#888',
  },
  changePositive: {
    fontSize: 12,
    color: '#1BA94C',
    fontWeight: 600,
  },
  changeNegative: {
    fontSize: 12,
    color: '#E8463A',
    fontWeight: 600,
  },
}

export default function StatCard({ label, value, icon, sub, change, accent }) {
  const isPositive = typeof change === 'string' && change.startsWith('+')
  const isNegative = typeof change === 'string' && change.startsWith('-')

  return (
    <div
      style={{
        ...styles.card,
        borderLeft: accent ? `4px solid ${accent}` : '1px solid #E0E0E0',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(27,169,76,0.12)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      <div style={styles.header}>
        <span style={styles.label}>{label}</span>
        {icon && <span style={styles.icon}>{icon}</span>}
      </div>
      <div style={styles.value}>{value}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {sub && <span style={styles.sub}>{sub}</span>}
        {change && (
          <span style={isPositive ? styles.changePositive : isNegative ? styles.changeNegative : styles.sub}>
            {change}
          </span>
        )}
      </div>
    </div>
  )
}
