const API = 'http://localhost:8000';

function fmtN(n) { return n >= 1000 ? (n/1000).toFixed(1)+'K' : Math.round(n); }
function fmtR(n) { return '$'+n.toFixed(0); }
function getMomentum(s) { return s>15?'🔥':s>8?'📈':s>3?'➡️':'📉'; }

// Load trending
async function loadTrending() {
  const list = document.getElementById('trendingList');
  try {
    const res = await fetch(API + '/api/trending');
    const data = await res.json();
    const top3 = data.slice(0, 3);
    if (!top3.length) {
      list.innerHTML = '<p class="loading">No trending data yet.</p>';
      return;
    }
    list.innerHTML = top3.map((p, i) => `
      <div class="trending-item" onclick="window.open('${p.url||'#'}','_blank')">
        <div class="trending-rank">#${i+1} Trending</div>
        <div class="trending-name">${p.title || 'Unknown Product'}</div>
        <div class="trending-meta">
          <span class="trending-momentum">${p.momentum_label || getMomentum(p.momentum_score||0)}</span>
          <span>${fmtN(p.monthly_sales||0)} sales/mo</span>
          <span class="result-rev">${fmtR(p.monthly_revenue||0)}/mo</span>
        </div>
      </div>
    `).join('');
    document.getElementById('apiStatus').textContent = '✓ API connected';
    document.getElementById('apiStatus').className = 'status ok';
  } catch {
    list.innerHTML = '<p class="loading">API offline — start with python start.py</p>';
    document.getElementById('apiStatus').textContent = '✗ API not running (localhost:8000)';
    document.getElementById('apiStatus').className = 'status error';
  }
}

// Search
async function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) return;
  const resultsEl = document.getElementById('searchResults');
  resultsEl.style.display = 'block';
  resultsEl.innerHTML = '<p class="loading">Searching...</p>';
  try {
    const res = await fetch(API + '/api/products?q=' + encodeURIComponent(q) + '&limit=5');
    const data = await res.json();
    if (!data.length) { resultsEl.innerHTML = '<p class="loading">No results found.</p>'; return; }
    resultsEl.innerHTML = data.map(p => `
      <div class="result-item">
        <div class="result-title">${p.title}</div>
        <div class="result-stats">
          <span>${getMomentum(p.momentum_score||0)}</span>
          <span>${fmtN(p.monthly_sales||0)}/mo</span>
          <span class="result-rev">${fmtR(p.monthly_revenue||0)}/mo</span>
          <span>Score: ${p.optimization_score||0}</span>
        </div>
      </div>
    `).join('');
  } catch {
    resultsEl.innerHTML = '<p class="loading">API offline.</p>';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadTrending();

  document.getElementById('searchBtn').addEventListener('click', doSearch);
  document.getElementById('searchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
  });

  document.getElementById('openPlatform').addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:3000' });
  });
});
