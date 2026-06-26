/**
 * TPT Analyzer — Mock API
 * Provides realistic demo data when the backend is unavailable.
 * Automatically used as fallback on all API calls.
 */

// ── Algorithm ──────────────────────────────────────────────────────────────────

function calcAgeMois(datePublished) {
  if (!datePublished) return 12
  try {
    const pub = new Date(datePublished)
    const now = new Date()
    return Math.max(1, (now.getFullYear() - pub.getFullYear()) * 12 + (now.getMonth() - pub.getMonth()))
  } catch { return 12 }
}

function enrich(p, keyword = '') {
  const age = calcAgeMois(p.date_published)
  const { reviews_total: rt = 0, reviews_30j: r30 = 0, favoris: fav = 0,
          downloads: dl = 0, has_bestseller: bs = false, has_image: img = true,
          desc_words: dw = 0, price = 0, rating = 0, title = '' } = p

  const base = rt * 12
  const bonus = bs ? 1.3 : 1.0
  const corr = age < 6 ? 1.4 : age <= 24 ? 1.0 : 0.85
  const total = (base + fav * 3 + dl * 0.8) * bonus * corr
  const monthly = total / Math.max(age, 1)
  const mom = rt > 0 ? (r30 / rt) * 100 : 0

  let optim = 0
  if (keyword && title.toLowerCase().includes(keyword.toLowerCase())) optim += 25
  if (rating > 3.8) optim += 20
  if (price >= 3 && price <= 15) optim += 20
  if (bs) optim += 15
  if (img) optim += 10
  if (dw > 200) optim += 10

  return {
    ...p,
    age_mois: age,
    total_sales: Math.round(total),
    monthly_sales: Math.round(monthly),
    monthly_revenue: Math.round(monthly * price * 0.55 * 100) / 100,
    total_revenue: Math.round(total * price * 0.55 * 100) / 100,
    momentum: Math.round(mom * 100) / 100,
    momentum_label: mom > 15 ? '🔥' : mom >= 8 ? '📈' : mom >= 3 ? '➡️' : '📉',
    optim_score: Math.min(100, optim),
  }
}

// ── Data ───────────────────────────────────────────────────────────────────────

const SHOPS = [
  ['The Moffatt Girls', 'the-moffatt-girls'],
  ['Deanna Jump', 'deanna-jump'],
  ['Rachel Lynette', 'rachel-lynette'],
  ['Lucky Little Learners', 'lucky-little-learners'],
  ['Fun in Fifth Grade', 'fun-in-fifth-grade'],
  ['The Curriculum Corner', 'the-curriculum-corner'],
  ['Reagan Tunstall', 'reagan-tunstall'],
  ['Jennifer Findley', 'jennifer-findley'],
  ['Lindsay Bowden', 'lindsay-bowden'],
  ['Appletastic Learning', 'appletastic-learning'],
]
const CATS = ['Math', 'ELA', 'Science', 'Social Studies', 'SEL', 'Back to School', 'Teacher Tools', 'Classroom Decor', 'Special Education', 'Foreign Language']
const GRADES = ['K-2', '3-5', '6-8', '9-12', 'PreK', 'All Grades']
const PRICES = [1.50, 2.00, 3.00, 4.00, 5.00, 6.00, 7.50, 8.00, 10.00, 12.00, 15.00, 20.00]
const TITLE_TPLS = [
  '{kw} Activities Bundle | Printable Worksheets',
  '{kw} Unit Study | Complete Curriculum Pack',
  '{kw} Task Cards | Boom Cards Digital',
  'Interactive {kw} Notebook | Foldables',
  '{kw} Assessment Pack | Tests & Quizzes',
  '{kw} Centers & Games | Differentiated',
  '{kw} Anchor Charts | Posters & Display',
  'Digital {kw} Activities | Google Slides',
  '{kw} Lesson Plans | Full Year Bundle',
  '{kw} Exit Tickets | Quick Checks',
]

// Seeded pseudo-random (reproducible per keyword)
function seededRng(seed) {
  let s = Math.abs(seed) % 2147483647
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646 }
}

export function generateMock(keyword = 'math', count = 20) {
  const rng = seededRng(keyword.split('').reduce((a, c) => a + c.charCodeAt(0), 0))
  const pick = arr => arr[Math.floor(rng() * arr.length)]
  const kw = keyword.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return Array.from({ length: count }, (_, i) => {
    const [shopName, shopSlug] = pick(SHOPS)
    const rt = Math.floor(rng() * 2990) + 10
    const r30 = Math.floor(rng() * Math.max(1, rt / 8))
    const fav = Math.floor(rng() * rt * 2) + 5
    const dl = Math.floor(rng() * rt * 14) + rt
    const bs = rng() < 0.2
    const price = pick(PRICES)
    const rating = Math.round((rng() * 1.5 + 3.5) * 10) / 10
    const dw = Math.floor(rng() * 400) + 100
    const ageY = rng() * 7.5 + 0.5
    const pubYear = new Date().getFullYear() - Math.floor(ageY)
    const pubMonth = Math.floor(rng() * 12) + 1
    const pid = Math.abs(keyword.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 1000 + i * 7919) % 9999999

    const p = {
      id: pid,
      url: `https://www.teacherspayteachers.com/Product/${kw.toLowerCase().replace(/\s+/g, '-')}-${pid}`,
      title: pick(TITLE_TPLS).replace('{kw}', kw),
      price,
      rating,
      reviews_total: rt,
      reviews_30j: r30,
      favoris: fav,
      downloads: dl,
      has_bestseller: bs,
      has_image: true,
      desc_words: dw,
      category: pick(CATS),
      grade_level: pick(GRADES),
      shop_name: shopName,
      shop_url: `https://www.teacherspayteachers.com/Store/${shopSlug}`,
      date_published: `${pubYear}-${String(pubMonth).padStart(2, '0')}-01`,
      thumbnail: `https://picsum.photos/seed/${pid}/120/90`,
      keyword_searched: keyword,
      scraped_at: new Date().toISOString(),
    }
    return enrich(p, keyword)
  })
}

// ── Category metadata ──────────────────────────────────────────────────────────

const CAT_META = [
  { slug: 'math', name: 'Math', icon: '📐', count: 847, momentum: 12 },
  { slug: 'ela-english-language-arts', name: 'ELA', icon: '📖', count: 1203, momentum: 9 },
  { slug: 'science', name: 'Science', icon: '🔬', count: 621, momentum: 5 },
  { slug: 'social-studies-history', name: 'Social Studies', icon: '🌍', count: 589, momentum: 4 },
  { slug: 'social-emotional-learning', name: 'SEL', icon: '💚', count: 432, momentum: 18 },
  { slug: 'back-to-school', name: 'Back to School', icon: '🎒', count: 389, momentum: 22 },
  { slug: 'teacher-tools', name: 'Teacher Tools', icon: '🛠️', count: 512, momentum: 6 },
  { slug: 'classroom-decor', name: 'Classroom Decor', icon: '🎨', count: 774, momentum: 5 },
  { slug: 'special-education', name: 'Special Education', icon: '⭐', count: 318, momentum: 7 },
  { slug: 'foreign-language', name: 'Foreign Language', icon: '🌐', count: 245, momentum: 4 },
]

function momentumLabel(m) {
  return m > 15 ? '🔥' : m >= 8 ? '📈' : m >= 3 ? '➡️' : '📉'
}

// ── Mock API responses ─────────────────────────────────────────────────────────

export const mockApi = {
  '/api/stats': () => ({
    total_products: 2847,
    trending_count: 23,
    top_revenue: 4829.10,
    best_category: 'SEL',
    total_stores: 10,
    avg_optim_score: 68.4,
  }),

  '/api/trending': (params) => {
    const all = [...generateMock('sel', 15), ...generateMock('back-to-school', 15), ...generateMock('math', 10)]
    return all.filter(p => p.momentum > 15).sort((a, b) => b.momentum - a.momentum).slice(0, params?.limit || 10)
  },

  '/api/categories': () => CAT_META.map(c => ({
    category: c.name,
    slug: c.slug,
    product_count: c.count,
    avg_rating: 4.1,
    total_reviews: c.count * 50,
    avg_momentum: momentumLabel(c.momentum),
    icon: c.icon,
  })),

  '/api/products': (params) => {
    const kw = params?.q || params?.category || 'math'
    return generateMock(kw, Math.min(params?.limit || 20, 30))
  },

  '/api/category/:slug/products': (params) => generateMock(params.slug, 25),

  '/api/stores': (params) => {
    const name = params?.name || 'the-moffatt-girls'
    const products = generateMock(name, 15).map(p => ({
      ...p,
      shop_name: name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      shop_url: `https://www.teacherspayteachers.com/Store/${name}`,
    }))
    const totalRev = products.reduce((s, p) => s + (p.total_revenue || 0), 0)
    const avgMom = products.reduce((s, p) => s + (p.momentum || 0), 0) / products.length
    return {
      store_name: name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      shop_url: `https://www.teacherspayteachers.com/Store/${name}`,
      product_count: products.length,
      total_revenue: Math.round(totalRev),
      avg_momentum: Math.round(avgMom * 100) / 100,
      avg_momentum_label: momentumLabel(avgMom),
      best_sellers_count: products.filter(p => p.has_bestseller).length,
      products,
    }
  },

  '/api/saved': () => [],
}

// ── Axios interceptor ──────────────────────────────────────────────────────────

import axios from 'axios'

let interceptorInstalled = false

export function installMockFallback() {
  if (interceptorInstalled) return
  interceptorInstalled = true

  axios.interceptors.response.use(
    response => response,
    async error => {
      const url = error?.config?.url || ''
      const params = error?.config?.params || {}
      const urlParams = new URLSearchParams(error?.config?.url?.split('?')[1] || '')
      const allParams = { ...params }
      urlParams.forEach((v, k) => { allParams[k] = v })

      // Match route and return mock data
      for (const [route, handler] of Object.entries(mockApi)) {
        const routeBase = route.split('?')[0]
        const urlBase = url.split('?')[0]

        if (urlBase === routeBase || urlBase.startsWith(routeBase.replace(':slug', '').replace(':id', ''))) {
          // Extract slug from URL
          const slugMatch = urlBase.match(/\/api\/category\/([^/]+)\/products/)
          if (slugMatch) allParams.slug = slugMatch[1]

          const storeMatch = urlBase.match(/\/api\/stores/)
          if (storeMatch) allParams.name = allParams.name || urlParams.get('name') || 'the-moffatt-girls'

          const data = handler(allParams)
          console.log(`[mockApi] Serving mock for ${urlBase}`)
          return { data, status: 200, headers: {}, config: error.config }
        }
      }

      return Promise.reject(error)
    }
  )
}
