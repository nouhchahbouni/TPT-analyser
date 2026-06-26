"""TPT Analyzer — FastAPI Backend"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import io
import csv
from typing import Optional, List
from datetime import datetime

import database as db
import scraper as sc
from calculator import enrich_product, get_momentum_label
from models import SaveProductRequest, DashboardStats

app = FastAPI(title="TPT Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        await db.init_db()
    except Exception as e:
        print(f"[startup] DB init failed (will use mock data): {e}")
    try:
        await sc.preload_demo_data()
    except Exception as e:
        print(f"[startup] preload failed (non-fatal): {e}")


# ─────────────────────────────── Products ─────────────────────────────────────

@app.get("/api/products")
async def get_products(
    q: str = "",
    limit: int = Query(50, le=200),
    offset: int = 0,
    category: str = "",
    shop_name: str = "",
):
    try:
        products = await db.get_products(q=q, limit=limit, offset=offset,
                                         category=category, shop_name=shop_name)
        enriched = [enrich_product(p, q or category or shop_name) for p in products]
    except Exception as e:
        print(f"[products] DB error: {e}")
        enriched = []

    # Always return data — use mock if DB is empty or failed
    if not enriched:
        keyword = q or category or shop_name or "math"
        enriched = sc.generate_mock_products(keyword, count=20)

    return enriched


@app.get("/api/product/{product_id}")
async def get_product(product_id: int):
    try:
        product = await db.get_product_by_id(product_id)
        if product:
            return enrich_product(product)
    except Exception as e:
        print(f"[product] DB error: {e}")
    raise HTTPException(status_code=404, detail="Product not found")


# ─────────────────────────────── Stores ───────────────────────────────────────

@app.get("/api/stores")
async def get_stores(name: str = ""):
    try:
        products = await db.get_products(shop_name=name, limit=100)
        enriched = [enrich_product(p, name) for p in products] if products else []
    except Exception as e:
        print(f"[stores] DB error: {e}")
        enriched = []

    if not enriched and name:
        enriched = sc.generate_mock_products(name, count=15)
        for p in enriched:
            p["shop_name"] = name.replace("-", " ").title()
            p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{name}"

    store_name_display = name.replace("-", " ").title() if name else "Store"
    total_rev = sum(p.get("total_revenue", 0) for p in enriched)
    avg_momentum = sum(p.get("momentum", 0) for p in enriched) / max(len(enriched), 1)
    bs_count = sum(1 for p in enriched if p.get("has_bestseller"))

    return {
        "store_name": store_name_display,
        "shop_url": f"https://www.teacherspayteachers.com/Store/{name}",
        "product_count": len(enriched),
        "total_revenue": round(total_rev, 2),
        "avg_momentum": round(avg_momentum, 2),
        "avg_momentum_label": get_momentum_label(avg_momentum),
        "best_sellers_count": bs_count,
        "products": enriched,
    }


# ─────────────────────────────── Categories ───────────────────────────────────

@app.get("/api/categories")
async def get_categories():
    try:
        cats = await db.get_categories()
    except Exception as e:
        print(f"[categories] DB error: {e}")
        cats = []

    existing_slugs = {c.get("slug", c.get("category", "").lower().replace(" ", "-")) for c in cats}

    for cat_slug in sc.CATEGORIES:
        display = cat_slug.replace("-", " ").title()
        if cat_slug not in existing_slugs and display.lower().replace(" ", "-") not in existing_slugs:
            cats.append({
                "category": display,
                "slug": cat_slug,
                "product_count": sc.CATEGORY_PRODUCT_COUNTS.get(cat_slug, 0),
                "avg_rating": 4.0,
                "total_reviews": 0,
                "avg_momentum": get_momentum_label(sc.CATEGORY_MOMENTUM.get(cat_slug, 5)),
                "icon": sc.CATEGORY_ICONS.get(cat_slug, "📚"),
            })

    for c in cats:
        if "slug" not in c:
            c["slug"] = c["category"].lower().replace(" ", "-")
        if "icon" not in c:
            c["icon"] = sc.CATEGORY_ICONS.get(c["slug"], "📚")
        if "avg_momentum" not in c or not isinstance(c["avg_momentum"], str):
            c["avg_momentum"] = get_momentum_label(sc.CATEGORY_MOMENTUM.get(c.get("slug", ""), 5))

    return cats


@app.get("/api/category/{slug}/products")
async def get_category_products(slug: str, limit: int = 50, offset: int = 0):
    display = slug.replace("-", " ").title()
    try:
        products = await db.get_products(category=display, limit=limit, offset=offset)
        if not products:
            products = await db.get_products(category=slug, limit=limit, offset=offset)
        enriched = [enrich_product(p, slug) for p in products]
    except Exception as e:
        print(f"[category products] DB error: {e}")
        enriched = []

    if not enriched:
        enriched = sc.generate_mock_products(slug, count=20)
        for p in enriched:
            p["category"] = display

    return enriched


# ─────────────────────────────── Saved ────────────────────────────────────────

@app.get("/api/saved")
async def get_saved():
    try:
        saved = await db.get_saved_products()
        return [enrich_product(p) for p in saved]
    except Exception as e:
        print(f"[saved] DB error: {e}")
        return []


@app.post("/api/saved")
async def save_product(body: SaveProductRequest):
    try:
        existing = await db.get_product_by_id(body.product_id) if body.product_id else None
        if not existing and body.url:
            product_data = {
                "url": body.url, "title": body.title or "Unknown",
                "price": 0.0, "rating": 0.0, "reviews_total": 0, "reviews_30j": 0,
                "favoris": 0, "downloads": 0, "has_bestseller": False, "has_image": True,
                "desc_words": 0, "category": "", "grade_level": "", "shop_name": "",
                "shop_url": "", "date_published": "", "thumbnail": "",
                "keyword_searched": "", "scraped_at": datetime.now().isoformat(),
            }
            product_id = await db.upsert_product(product_data)
        else:
            product_id = body.product_id or 0

        saved_id = await db.save_product(product_id, body.notes or "")
        return {"id": saved_id, "product_id": product_id, "status": "saved"}
    except Exception as e:
        print(f"[save] DB error: {e}")
        raise HTTPException(status_code=500, detail="Could not save product")


@app.delete("/api/saved/{saved_id}")
async def delete_saved(saved_id: int):
    try:
        await db.delete_saved_product(saved_id)
    except Exception as e:
        print(f"[delete saved] DB error: {e}")
    return {"status": "deleted", "id": saved_id}


# ─────────────────────────────── Scraping ─────────────────────────────────────

@app.post("/api/scrape/keyword")
async def scrape_keyword_endpoint(q: str, background_tasks: BackgroundTasks):
    if not q:
        raise HTTPException(status_code=400, detail="Keyword required")
    background_tasks.add_task(sc.scrape_keyword, q, use_cache=False)
    return {"status": "started", "keyword": q}


@app.post("/api/scrape/store")
async def scrape_store_endpoint(name: str, background_tasks: BackgroundTasks):
    if not name:
        raise HTTPException(status_code=400, detail="Store name required")
    background_tasks.add_task(sc.scrape_store, name)
    return {"status": "started", "store": name}


# ─────────────────────────────── Trending ─────────────────────────────────────

@app.get("/api/trending")
async def get_trending(limit: int = 10):
    try:
        products = await db.get_products(limit=500)
        enriched = [enrich_product(p) for p in products]
        trending = sorted([p for p in enriched if p.get("momentum", 0) > 15],
                          key=lambda x: x.get("momentum", 0), reverse=True)
    except Exception as e:
        print(f"[trending] DB error: {e}")
        trending = []

    if not trending:
        mock = sc.generate_mock_products("trending", count=30)
        trending = sorted([p for p in mock if p.get("momentum", 0) > 15],
                          key=lambda x: x.get("momentum", 0), reverse=True)

    return trending[:limit]


# ─────────────────────────────── Stats ────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    try:
        db_stats = await db.get_db_stats()
        products = await db.get_products(limit=1000)
        enriched = [enrich_product(p) for p in products]
    except Exception as e:
        print(f"[stats] DB error: {e}")
        db_stats = {"total_products": 0, "total_stores": 0, "avg_rating": 0}
        enriched = sc.generate_mock_products("all", count=50)

    trending_count = sum(1 for p in enriched if p.get("momentum", 0) > 15)
    top_revenue = max((p.get("monthly_revenue", 0) for p in enriched), default=0)

    cat_reviews: dict = {}
    for p in enriched:
        cat = p.get("category", "Unknown")
        cat_reviews[cat] = cat_reviews.get(cat, 0) + p.get("reviews_total", 0)
    best_category = max(cat_reviews, key=cat_reviews.get) if cat_reviews else "Math"
    avg_optim = sum(p.get("optim_score", 0) for p in enriched) / max(len(enriched), 1)

    total = db_stats.get("total_products", 0) or len(enriched)

    return DashboardStats(
        total_products=total,
        trending_count=trending_count,
        top_revenue=round(top_revenue, 2),
        best_category=best_category,
        total_stores=db_stats.get("total_stores", 0),
        avg_optim_score=round(avg_optim, 1),
    )


# ─────────────────────────────── Export CSV ───────────────────────────────────

@app.get("/api/export/csv")
async def export_csv(q: str = "", category: str = ""):
    try:
        products = await db.get_products(q=q, category=category, limit=10000)
        enriched = [enrich_product(p, q or category) for p in products]
    except Exception:
        enriched = sc.generate_mock_products(q or category or "export", count=50)

    output = io.StringIO()
    fieldnames = [
        "id", "title", "price", "rating", "reviews_total", "reviews_30j",
        "total_sales", "monthly_sales", "monthly_revenue", "total_revenue",
        "momentum", "momentum_label", "optim_score", "has_bestseller",
        "category", "grade_level", "shop_name", "url", "scraped_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for p in enriched:
        writer.writerow(p)

    output.seek(0)
    filename = f"tpt_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─────────────────────────────── Health ───────────────────────────────────────

@app.get("/api/debug/env")
async def debug_env():
    key = os.getenv("SCRAPINGBEE_API_KEY", "")
    return {
        "key_set": bool(key),
        "key_length": len(key),
        "key_preview": key[:6] + "..." if key else "EMPTY",
        "all_vars": [k for k in os.environ.keys() if "SCRAPING" in k or "BEE" in k],
    }

@app.get("/api/health")
async def health():
    db_ok = False
    try:
        stats = await db.get_db_stats()
        db_ok = True
    except Exception:
        pass
    return {
        "status": "ok",
        "version": "1.0.0",
        "db_connected": db_ok,
        "has_neon": bool(os.getenv("DATABASE_URL")),
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────── Serve React SPA ──────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = os.path.join(STATIC_DIR, "index.html")
        return FileResponse(index)
