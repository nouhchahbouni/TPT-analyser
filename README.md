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
