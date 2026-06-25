/**
 * TPT Analyzer — Content Script
 * Injects analysis overlays on TeachersPayTeachers pages.
 */

const API = 'http://localhost:8000'
const PAGE_URL = window.location.href

// ─── Utility functions ──────────────────────────────────────────────────────

function fmt(n) {
  if (typeof n !== 'number') return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

function fmtRev(n) {
  if (typeof n !== 'number') return '—'
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function getMomentumLabel(m) {
  if (m > 15) return '🔥'
  if (m >= 8) return '📈'
  if (m >= 3) return '➡️'
  return '📉'
}

// Quick local estimate when API is unavailable
function estimateFromCard(card) {
  const titleEl = card.querySelector('h2, h3, [class*="title"]')
  const title = titleEl ? titleEl.textContent.trim() : 'Unknown Product'

  const priceEl = card.querySelector('[class*="price"]')
  let price = 5.0
  if (priceEl) {
    const m = priceEl.textContent.match(/[\d.]+/)
    if (m) price = parseFloat(m[0])
  }

  const ratingEl = card.querySelector('[aria-label*="rating"], [aria-label*="star"]')
  let rating = 4.2
  if (ratingEl) {
    const label = ratingEl.getAttribute('aria-label') || ''
    const m = label.match(/([\d.]+)/)
    if (m) rating = parseFloat(m[1])
  }

  const reviewEl = card.querySelector('[class*="rating-count"], [class*="review"]')
  let reviews = 100
  if (reviewEl) {
    const m = reviewEl.textContent.match(/[\d,]+/)
    if (m) reviews = parseInt(m[0].replace(/,/g, ''))
  }

  const hasBestseller = !!card.querySelector('[class*="bestseller"], [class*="badge"]')

  // Apply algorithm
  const totalSales = (reviews * 12 + reviews * 2 * 3) * (hasBestseller ? 1.3 : 1.0) * 1.0
  const monthSales = totalSales / 12
  const monthRev = monthSales * price * 0.55
  const reviews30 = Math.floor(reviews * 0.07)
  const momentum = reviews > 0 ? (reviews30 / reviews) * 100 : 5
  const optimScore = (
    (price >= 3 && price <= 15 ? 20 : 0) +
    (rating > 3.8 ? 20 : 0) +
    (hasBestseller ? 15 : 0) +
    25 + 10  // keyword + image assumed
  )

  return { title, price, rating, reviews, totalSales, monthSales, monthRev, momentum, optimScore, hasBestseller }
}

function createOptimCircle(score) {
  const color = score >= 80 ? '#1BA94C' : score >= 60 ? '#4CAF50' : score >= 40 ? '#FF8F00' : '#E8463A'
  return `
    <div style="position:relative;width:38px;height:38px;flex-shrink:0">
      <svg width="38" height="38" style="transform:rotate(-90deg)">
        <circle cx="19" cy="19" r="15" fill="none" stroke="#E0E0E0" stroke-width="3"/>
        <circle cx="19" cy="19" r="15" fill="none" stroke="${color}" stroke-width="3"
          stroke-dasharray="${(score / 100) * 94.2} 94.2" stroke-linecap="round"/>
      </svg>
      <span style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:10px;font-weight:700;color:${color}">${score}</span>
    </div>
  `
}

function createBar(data) {
  const momentumLabel = getMomentumLabel(data.momentum)
  const momentumBg = data.momentum > 15 ? '#FFF0EE' : data.momentum >= 8 ? '#E8F5E9' : '#F5F5F5'
  const momentumColor = data.momentum > 15 ? '#E8463A' : data.momentum >= 8 ? '#0D7A35' : '#666'

  const bar = document.createElement('div')
  bar.className = 'tpt-analyzer-bar'
  bar.innerHTML = `
    <div style="display:flex;align-items:center;gap:6px;font-weight:700;font-size:11px;color:#1BA94C;flex-shrink:0">
      <span style="background:#1BA94C;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">TPT</span>
      Analyzer
    </div>
    <div class="tpt-analyzer-stat">
      <span class="tpt-analyzer-label">Mo. Sales</span>
      <span class="tpt-analyzer-value">${fmt(data.monthSales)}</span>
    </div>
    <div class="tpt-analyzer-stat">
      <span class="tpt-analyzer-label">Total Sales</span>
      <span class="tpt-analyzer-value">${fmt(data.totalSales)}</span>
    </div>
    <div class="tpt-analyzer-stat">
      <span class="tpt-analyzer-label">Mo. Revenue</span>
      <span class="tpt-analyzer-value" style="color:#1BA94C">${fmtRev(data.monthRev)}</span>
    </div>
    <div class="tpt-analyzer-stat">
      <span class="tpt-analyzer-label">Momentum</span>
      <span style="display:inline-flex;align-items:center;gap:4px;padding:2px 7px;border-radius:12px;font-size:11px;font-weight:700;background:${momentumBg};color:${momentumColor}">
        ${momentumLabel} ${data.momentum.toFixed(1)}%
      </span>
    </div>
    <div class="tpt-analyzer-stat">
      <span class="tpt-analyzer-label">Optim</span>
      ${createOptimCircle(data.optimScore)}
    </div>
    <button class="tpt-analyzer-save-btn" data-title="${encodeURIComponent(data.title)}">+ Save</button>
  `

  bar.querySelector('.tpt-analyzer-save-btn').addEventListener('click', function () {
    this.textContent = '✓ Saved'
    this.classList.add('saved')
    chrome.runtime.sendMessage({
      type: 'SAVE_PRODUCT',
      product: {
        product_id: 0,
        url: window.location.href,
        title: decodeURIComponent(this.dataset.title),
        notes: ''
      }
    })
  })

  return bar
}

// ─── Browse / Search page ────────────────────────────────────────────────────

function injectSearchBars() {
  const cards = document.querySelectorAll(
    '[data-testid="product-card"], .ProductRowCard, .ProductListingCard, [class*="ProductCard"]'
  )

  cards.forEach(card => {
    if (card.querySelector('.tpt-analyzer-bar')) return  // already injected

    const data = estimateFromCard(card)
    const bar = createBar(data)

    // Insert after the card or inside it
    const parent = card.parentElement
    if (parent) {
      parent.insertBefore(bar, card.nextSibling)
    } else {
      card.appendChild(bar)
    }
  })
}

// ─── Product detail page ─────────────────────────────────────────────────────

async function injectProductPanel() {
  if (document.querySelector('.tpt-analyzer-panel')) return

  const panel = document.createElement('div')
  panel.className = 'tpt-analyzer-panel'
  panel.innerHTML = `
    <div class="tpt-analyzer-panel-header">
      <span class="tpt-analyzer-logo-mini">TPT</span>
      <div>
        <div style="font-weight:700;font-size:14px">TPT Analyzer</div>
        <div style="font-size:11px;opacity:0.8">Sales Estimates</div>
      </div>
      <button id="tptPanelClose" style="margin-left:auto;background:none;border:none;color:#fff;cursor:pointer;font-size:18px">×</button>
    </div>
    <div class="tpt-analyzer-panel-body">
      <div class="tpt-analyzer-big-score">
        <div class="tpt-analyzer-score-circle" id="tptOptimCircle">—</div>
        <div style="font-size:12px;font-weight:600;color:#666">Optimization Score</div>
      </div>
      <div id="tptPanelRows">
        <div style="text-align:center;padding:20px;color:#888;font-size:13px">Analyzing product...</div>
      </div>
      <button id="tptSaveBtn" style="width:100%;background:#1BA94C;color:#fff;border:none;border-radius:8px;padding:10px;font-size:14px;font-weight:700;cursor:pointer;margin-top:12px;font-family:Inter,sans-serif">
        + Save Product
      </button>
      <a href="http://localhost:3000" target="_blank"
        style="display:block;text-align:center;margin-top:8px;font-size:12px;color:#1BA94C;font-weight:600;text-decoration:none">
        Open Full Analyzer →
      </a>
    </div>
  `

  document.body.appendChild(panel)

  panel.querySelector('#tptPanelClose').addEventListener('click', () => panel.remove())
  panel.querySelector('#tptSaveBtn').addEventListener('click', function () {
    this.textContent = '✓ Saved!'
    this.style.background = '#666'
    this.disabled = true
    chrome.runtime.sendMessage({
      type: 'SAVE_PRODUCT',
      product: {
        product_id: 0,
        url: window.location.href,
        title: document.title,
        notes: ''
      }
    })
  })

  // Try to get real data from API, fall back to page scraping
  try {
    const titleEl = document.querySelector('h1, [data-testid="product-title"]')
    const title = titleEl ? titleEl.textContent.trim() : document.title

    const priceEl = document.querySelector('[data-testid="price"], [class*="price"]')
    let price = 5.0
    if (priceEl) {
      const m = priceEl.textContent.match(/[\d.]+/)
      if (m) price = parseFloat(m[0])
    }

    const ratingEl = document.querySelector('[aria-label*="rating"]')
    let rating = 4.0
    if (ratingEl) {
      const m = (ratingEl.getAttribute('aria-label') || '').match(/([\d.]+)/)
      if (m) rating = parseFloat(m[1])
    }

    const reviewEl = document.querySelector('[class*="rating-count"]')
    let reviews = 100
    if (reviewEl) {
      const m = reviewEl.textContent.match(/[\d,]+/)
      if (m) reviews = parseInt(m[0].replace(/,/g, ''))
    }

    const hasBestseller = !!document.querySelector('[class*="bestseller"]')
    const reviews30 = Math.floor(reviews * 0.07)
    const momentum = reviews > 0 ? (reviews30 / reviews) * 100 : 5
    const totalSales = (reviews * 12) * (hasBestseller ? 1.3 : 1.0)
    const monthSales = totalSales / 12
    const monthRev = monthSales * price * 0.55
    const optimScore = (
      (price >= 3 && price <= 15 ? 20 : 0) +
      (rating > 3.8 ? 20 : 0) +
      (hasBestseller ? 15 : 0) +
      10 + 25  // image + title keyword
    )
    const momentumLabel = getMomentumLabel(momentum)

    const circleEl = document.getElementById('tptOptimCircle')
    if (circleEl) {
      const color = optimScore >= 80 ? '#1BA94C' : optimScore >= 60 ? '#4CAF50' : optimScore >= 40 ? '#FF8F00' : '#E8463A'
      circleEl.style.borderColor = color
      circleEl.style.color = color
      circleEl.textContent = optimScore
    }

    const rows = [
      { label: 'Monthly Sales', value: fmt(monthSales), accent: false },
      { label: 'Total Sales', value: fmt(totalSales), accent: false },
      { label: 'Monthly Revenue', value: fmtRev(monthRev), accent: true },
      { label: 'Momentum', value: `${momentumLabel} ${momentum.toFixed(1)}%`, accent: false },
      { label: 'Rating', value: `★ ${rating.toFixed(1)}`, accent: false },
      { label: 'Reviews', value: fmt(reviews), accent: false },
      { label: 'Best Seller', value: hasBestseller ? '🏆 Yes' : 'No', accent: false },
    ]

    const rowsEl = document.getElementById('tptPanelRows')
    if (rowsEl) {
      rowsEl.innerHTML = rows.map(r => `
        <div class="tpt-analyzer-panel-row">
          <span style="font-size:12px;color:#666;font-weight:600">${r.label}</span>
          <span style="font-size:13px;font-weight:700;color:${r.accent ? '#1BA94C' : '#2D2D2D'}">${r.value}</span>
        </div>
      `).join('')
    }
  } catch (e) {
    const rowsEl = document.getElementById('tptPanelRows')
    if (rowsEl) rowsEl.innerHTML = '<div style="color:#E8463A;font-size:12px;text-align:center;padding:12px">Analysis unavailable</div>'
  }
}

// ─── Store page ──────────────────────────────────────────────────────────────

function injectStoreBanner() {
  if (document.querySelector('.tpt-analyzer-store-banner')) return

  const storeNameEl = document.querySelector('h1, [class*="store-name"], [class*="StoreName"]')
  const storeName = storeNameEl ? storeNameEl.textContent.trim() : 'This Store'

  // Estimate store stats from visible products
  const cards = document.querySelectorAll('[data-testid="product-card"], [class*="ProductCard"]')
  let totalRev = 0, totalProds = cards.length || 25, bsCount = 0

  cards.forEach(card => {
    const data = estimateFromCard(card)
    totalRev += data.monthRev || 0
    if (data.hasBestseller) bsCount++
  })

  const banner = document.createElement('div')
  banner.className = 'tpt-analyzer-store-banner'
  banner.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-right:12px">
      <div style="background:rgba(255,255,255,0.2);border-radius:6px;padding:4px 8px;font-weight:700;font-size:12px">TPT</div>
      <div>
        <div style="font-weight:700;font-size:15px">${escHtml(storeName)}</div>
        <div style="font-size:11px;opacity:0.8">TPT Analyzer Insights</div>
      </div>
    </div>
    <div class="tpt-analyzer-store-stat">
      <span class="tpt-analyzer-store-stat-label">Est. Mo. Revenue</span>
      <span class="tpt-analyzer-store-stat-value">${fmtRev(totalRev)}</span>
    </div>
    <div class="tpt-analyzer-store-stat">
      <span class="tpt-analyzer-store-stat-label">Products</span>
      <span class="tpt-analyzer-store-stat-value">${totalProds}+</span>
    </div>
    <div class="tpt-analyzer-store-stat">
      <span class="tpt-analyzer-store-stat-label">Best Sellers</span>
      <span class="tpt-analyzer-store-stat-value">${bsCount}</span>
    </div>
    <button class="tpt-analyzer-open-btn" onclick="window.open('http://localhost:3000/stores','_blank')">
      Open Full Analysis →
    </button>
  `

  // Insert at the top of main content
  const main = document.querySelector('main, [role="main"], #main, .main-content') || document.body
  main.insertBefore(banner, main.firstChild)
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// ─── Router ──────────────────────────────────────────────────────────────────

function detectPageAndInject() {
  const url = window.location.href

  if (url.includes('/browse') || url.includes('/search') || url.includes('search=')) {
    // Search / browse page
    injectSearchBars()
    // Observe for new product cards loaded dynamically
    const observer = new MutationObserver(() => injectSearchBars())
    observer.observe(document.body, { childList: true, subtree: true })
  } else if (url.match(/\/Product\//i)) {
    // Individual product page
    injectProductPanel()
  } else if (url.match(/\/Store\//i)) {
    // Store page
    injectStoreBanner()
    injectSearchBars()
  }
}

// Run on load and after SPA navigation
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', detectPageAndInject)
} else {
  detectPageAndInject()
}

// Handle SPA navigation
let lastUrl = window.location.href
setInterval(() => {
  if (window.location.href !== lastUrl) {
    lastUrl = window.location.href
    setTimeout(detectPageAndInject, 1000)
  }
}, 500)
