"""TPT Analyzer — FastAPI Backend"""
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import csv
from typing import Optional, List
from datetime import datetime

import database as db
import scraper as sc
from calculator import enrich_product, calc_momentum, get_momentum_label
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
    await db.init_db()
    await sc.preload_demo_data()


# ─────────────────────────────── Products ────────────────────────────────────

@app.get("/api/products")
async def get_products(
    q: str = "",
    limit: int = Query(50, le=200),
    offset: int = 0,
    category: str = "",
    shop_name: str = "",
):
    products = await db.get_products(q=q, limit=limit, offset=offset,
                                     category=category, shop_name=shop_name)
    keyword = q or category or shop_name
    enriched = [enrich_product(p, keyword) for p in products]

    # If no results in DB, generate mock data
    if not enriched and q:
        enriched = sc.generate_mock_products(q, count=20)

    return {"products": enriched, "total": len(enriched)}


@app.get("/api/product/{product_id}")
async def get_product(product_id: int):
    product = await db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return enrich_product(product)


# ─────────────────────────────── Stores ──────────────────────────────────────

@app.get("/api/stores")
async def get_stores(name: str = ""):
    products = await db.get_products(shop_name=name, limit=100)
    if not products and name:
        # Generate mock data for this store
        mock = sc.generate_mock_products(name, count=15)
        for p in mock:
            p["shop_name"] = name.replace("-", " ").title()
            p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{name}"
        products = mock
    else:
        products = [enrich_product(p, name) for p in products]

    if not products:
        # Return all distinct stores
        all_products = await db.get_products(limit=500)
        stores_map = {}
        for p in all_products:
            sn = p.get("shop_name", "")
            if sn and sn not in stores_map:
                stores_map[sn] = {
                    "shop_name": sn,
                    "shop_url": p.get("shop_url", ""),
                    "products": []
                }
            if sn:
                stores_map[sn]["products"].append(enrich_product(p, sn))

        result = []
        for sn, data in stores_map.items():
            prods = data["products"]
            total_rev = sum(p.get("total_revenue", 0) for p in prods)
            avg_momentum = sum(p.get("momentum", 0) for p in prods) / max(len(prods), 1)
            bs_count = sum(1 for p in prods if p.get("has_bestseller"))
            result.append({
                "shop_name": sn,
                "shop_url": data["shop_url"],
                "product_count": len(prods),
                "total_revenue": round(total_rev, 2),
                "avg_momentum": round(avg_momentum, 2),
                "bestseller_count": bs_count,
                "products": prods[:10],
            })
        return {"stores": result}

    # Summarize the store
    enriched = [enrich_product(p, name) for p in products] if products and "total_sales" not in products[0] else products
    total_rev = sum(p.get("total_revenue", 0) for p in enriched)
    avg_momentum = sum(p.get("momentum", 0) for p in enriched) / max(len(enriched), 1)
    bs_count = sum(1 for p in enriched if p.get("has_bestseller"))
    store_name_display = (enriched[0].get("shop_name") or name).replace("-", " ").title() if enriched else name

    return {
        "store": {
            "shop_name": store_name_display,
            "shop_url": f"https://www.teacherspayteachers.com/Store/{name}",
            "product_count": len(enriched),
            "total_revenue": round(total_rev, 2),
            "avg_momentum": round(avg_momentum, 2),
            "bestseller_count": bs_count,
        },
        "products": enriched,
    }


# ─────────────────────────────── Categories ──────────────────────────────────

@app.get("/api/categories")
async def get_categories():
    cats = await db.get_categories()
    # Add pre-defined categories not yet scraped
    existing = {c["category"] for c in cats}
    for cat in sc.CATEGORIES:
        display = cat.replace("-", " ").title()
        if display not in existing and cat not in existing:
            cats.append({
                "category": display,
                "slug": cat,
                "product_count": 0,
                "avg_rating": 0,
                "total_reviews": 0,
                "icon": sc.CATEGORY_ICONS.get(cat, "📚"),
            })
    for c in cats:
        c["icon"] = sc.CATEGORY_ICONS.get(c.get("slug", ""), sc.CATEGORY_ICONS.get(
            c["category"].lower().replace(" ", "-"), "📚"))
        if "slug" not in c:
            c["slug"] = c["category"].lower().replace(" ", "-")
    return {"categories": cats}


@app.get("/api/category/{slug}/products")
async def get_category_products(slug: str, limit: int = 50, offset: int = 0):
    display = slug.replace("-", " ").title()
    products = await db.get_products(category=display, limit=limit, offset=offset)
    if not products:
        products = await db.get_products(category=slug, limit=limit, offset=offset)
    if not products:
        products = sc.generate_mock_products(slug, count=20)
        for p in products:
            p["category"] = display
    else:
        products = [enrich_product(p, slug) for p in products]
    return {"products": products, "category": display, "total": len(products)}


# ─────────────────────────────── Saved ───────────────────────────────────────

@app.get("/api/saved")
async def get_saved():
    saved = await db.get_saved_products()
    enriched = [enrich_product(p) for p in saved]
    return {"saved": enriched}


@app.post("/api/saved")
async def save_product(body: SaveProductRequest):
    # If product_id doesn't exist yet, try to create it from body data
    existing = await db.get_product_by_id(body.product_id)
    if not existing and body.url:
        product_data = {
            "url": body.url,
            "title": body.title,
            "price": 0.0,
            "rating": 0.0,
            "reviews_total": 0,
            "reviews_30j": 0,
            "favoris": 0,
            "downloads": 0,
            "has_bestseller": False,
            "has_image": True,
            "desc_words": 0,
            "category": "",
            "grade_level": "",
            "shop_name": "",
            "shop_url": "",
            "date_published": "",
            "thumbnail": "",
            "keyword_searched": "",
            "scraped_at": datetime.now().isoformat(),
        }
        product_id = await db.upsert_product(product_data)
    else:
        product_id = body.product_id

    saved_id = await db.save_product(product_id, body.notes)
    return {"id": saved_id, "product_id": product_id, "status": "saved"}


@app.delete("/api/saved/{saved_id}")
async def delete_saved(saved_id: int):
    await db.delete_saved_product(saved_id)
    return {"status": "deleted", "id": saved_id}


# ─────────────────────────────── Scraping ────────────────────────────────────

@app.post("/api/scrape/keyword")
async def scrape_keyword(q: str, background_tasks: BackgroundTasks):
    if not q:
        raise HTTPException(status_code=400, detail="Keyword required")
    background_tasks.add_task(sc.scrape_keyword, q, use_cache=False)
    return {"status": "started", "keyword": q, "message": f"Scraping '{q}' in background"}


@app.post("/api/scrape/store")
async def scrape_store(name: str, background_tasks: BackgroundTasks):
    if not name:
        raise HTTPException(status_code=400, detail="Store name required")
    background_tasks.add_task(sc.scrape_store, name)
    return {"status": "started", "store": name, "message": f"Scraping store '{name}' in background"}


# ─────────────────────────────── Trending ────────────────────────────────────

@app.get("/api/trending")
async def get_trending(limit: int = 10):
    products = await db.get_products(limit=500)
    enriched = [enrich_product(p) for p in products]
    trending = [p for p in enriched if p.get("momentum", 0) > 15]
    trending.sort(key=lambda x: x.get("momentum", 0), reverse=True)

    if not trending:
        # Generate some trending mock products
        mock = sc.generate_mock_products("trending", count=20)
        trending = [p for p in mock if p.get("momentum", 0) > 15]
        trending.sort(key=lambda x: x.get("momentum", 0), reverse=True)

    return {"trending": trending[:limit]}


# ─────────────────────────────── Stats ───────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    db_stats = await db.get_db_stats()
    products = await db.get_products(limit=1000)
    enriched = [enrich_product(p) for p in products]

    trending_count = sum(1 for p in enriched if p.get("momentum", 0) > 15)
    top_revenue = max((p.get("monthly_revenue", 0) for p in enriched), default=0)

    # Best category by total reviews
    cat_reviews: dict = {}
    for p in enriched:
        cat = p.get("category", "Unknown")
        cat_reviews[cat] = cat_reviews.get(cat, 0) + p.get("reviews_total", 0)
    best_category = max(cat_reviews, key=cat_reviews.get) if cat_reviews else "Math"

    avg_optim = sum(p.get("optim_score", 0) for p in enriched) / max(len(enriched), 1)

    return DashboardStats(
        total_products=db_stats["total_products"],
        trending_count=trending_count,
        top_revenue=round(top_revenue, 2),
        best_category=best_category,
        total_stores=db_stats["total_stores"],
        avg_optim_score=round(avg_optim, 1),
    )


# ─────────────────────────────── Export ──────────────────────────────────────

@app.get("/api/export/csv")
async def export_csv(q: str = "", category: str = ""):
    products = await db.get_products(q=q, category=category, limit=10000)
    enriched = [enrich_product(p, q or category) for p in products]

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


# ─────────────────────────────── Health ──────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.now().isoformat()}
