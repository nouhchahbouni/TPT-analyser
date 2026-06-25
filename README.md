# TPT Analyzer

**Discover What's Selling on TPT Right Now**

## Quick Start

```bash
# 1. Install everything
python setup.py

# 2. Launch
python start.py

# 3. Open http://localhost:3000
```

## Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `./extension/` folder

## Architecture

```
TPT Analyzer
├── backend/        FastAPI + Playwright + SQLite (port 8000)
├── frontend/       React + Vite (port 3000)
├── extension/      Chrome Extension (Manifest V3)
├── setup.py        Auto-installer
└── start.py        Launch script
```

## Branding

- Green: `#1BA94C` · Dark green: `#0D7A35`
- Font: Inter / Nunito Sans

## Deployment (Vercel + Neon)

### Database (Neon)
1. Create account at neon.tech
2. Create a new project → copy the connection string
3. Add to Vercel env vars: `DATABASE_URL=postgresql://...`

### Deploy on Vercel
1. Import repo on vercel.com
2. Vercel auto-detects frontend + backend
3. Add env vars in Vercel dashboard:
   - `DATABASE_URL` (from Neon)
   - `VITE_API_URL` (your backend Vercel URL)
4. Click Deploy

### Local Development
```bash
cp .env.example .env
# Fill in DATABASE_URL or leave empty for SQLite fallback
python setup.py
python start.py
```
