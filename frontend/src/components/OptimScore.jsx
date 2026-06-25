import React from 'react'

function getColor(score) {
  if (score >= 80) return '#1BA94C'
  if (score >= 60) return '#4CAF50'
  if (score >= 40) return '#FF8F00'
  return '#E8463A'
}

export default function OptimScore({ score }) {
  const pct = Math.min(100, Math.max(0, score || 0))
  const color = getColor(pct)
  const radius = 18
  const circumference = 2 * Math.PI * radius
  const strokeDash = (pct / 100) * circumference

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <svg width={46} height={46} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={23} cy={23} r={radius}
          fill="none"
          stroke="#E0E0E0"
          strokeWidth={4}
        />
        <circle
          cx={23} cy={23} r={radius}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeDasharray={`${strokeDash} ${circumference}`}
          strokeLinecap="round"
        />
      </svg>
      <span style={{
        position: 'absolute',
        fontSize: 11,
        fontWeight: 700,
        color,
        lineHeight: 1,
      }}>
        {pct}
      </span>
    </div>
  )
}
