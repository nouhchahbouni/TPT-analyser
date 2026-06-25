import React from 'react'

const MOMENTUM_CONFIG = {
  '🔥': { bg: '#FFF0EE', color: '#E8463A', label: 'Hot' },
  '📈': { bg: '#E8F5E9', color: '#0D7A35', label: 'Rising' },
  '➡️': { bg: '#F5F5F5', color: '#666666', label: 'Stable' },
  '📉': { bg: '#FFF8E1', color: '#FF8F00', label: 'Declining' },
}

export default function MomentumBadge({ label, momentum, showValue = true }) {
  const cfg = MOMENTUM_CONFIG[label] || MOMENTUM_CONFIG['➡️']

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '3px 8px',
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 600,
      background: cfg.bg,
      color: cfg.color,
      whiteSpace: 'nowrap',
    }}>
      <span>{label}</span>
      {showValue && momentum !== undefined && (
        <span>{momentum.toFixed(1)}%</span>
      )}
    </span>
  )
}
