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
import json
import asyncio
from typing import Optional, List
from datetime import datetime

import database as db
import scraper as sc
from calculator import enrich_product, get_momentum_label
from algorithms import enrich_product_full
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
    asyncio.create_task(_auto_enrich_loop())


async def _auto_enrich_loop():
    """Auto-restart enrichment every hour if not running and products remain."""
    await asyncio.sleep(10)  # wait for app to fully start
    while True:
        try:
            if not _enrich_status.get("running"):
                # Priority 1: enrich products missing date_published
                missing = await db.get_all_missing_date(limit=5000)
                if missing:
                    print(f"[auto-enrich] {len(missing)} products missing date — starting enrichment")
                    asyncio.create_task(_run_enrich_all_missing())
                else:
                    print("[auto-enrich] All products enriched ✅")
        except Exception as e:
            print(f"[auto-enrich] check error: {e}")
        await asyncio.sleep(3600)  # check every hour


async def _run_enrich_all_missing():
    """Enrich all products missing date_published."""
    _enrich_status.update({"running": True, "done": 0, "total": 0, "errors": 0,
                            "started_at": datetime.now().isoformat()})
    try:
        products = await db.get_all_missing_date(limit=5000)
        _enrich_status["total"] = len(products)
        for p in products:
            if not _enrich_status["running"]:
                break
            try:
                product_data = await asyncio.get_event_loop().run_in_executor(
                    None, sc.fetch_product_graphql, p.get("url", "")
                )
                p.update(product_data)
                await db.upsert_product(p)
                _enrich_status["done"] += 1
            except Exception as e:
                _enrich_status["errors"] += 1
                print(f"[enrich-date] error: {e}")
    except Exception as e:
        print(f"[enrich-date] task error: {e}")
    finally:
        _enrich_status["running"] = False
        print(f"[enrich-date] Done: {_enrich_status['done']}/{_enrich_status['total']}")


# ─────────────────────────────── Products ─────────────────────────────────────

@app.get("/api/products")
async def get_products(
    q: str = "",
    limit: int = Query(50, le=300),
    offset: int = 0,
    category: str = "",
    shop_name: str = "",
    category_url: str = "",
    background_tasks: BackgroundTasks = None,
):
    keyword = q or category or shop_name or "math"

    # 1. Try the database (fast, cached results)
    try:
        products = await db.get_products(q=q, limit=limit, offset=offset,
                                         category=category, shop_name=shop_name,
                                         category_url=category_url)
        enriched = [enrich_product(p, keyword) for p in products]
    except Exception as e:
        print(f"[products] DB error: {e}")
        enriched = []

    # 2. If DB empty AND no specific filter → call Algolia live and cache results
    # Skip Algolia fallback when category_url/category/shop_name is specified (just return empty)
    if not enriched and not category_url and not category and not shop_name:
        try:
            loop = asyncio.get_event_loop()
            live_products = await loop.run_in_executor(
                None, sc.scrape_keyword_sync, keyword, min(limit, 40)
            )
            if live_products:
                enriched = live_products
                async def _store(prods):
                    for p in prods:
                        try:
                            await db.upsert_product(p)
                        except Exception:
                            pass
                if background_tasks:
                    background_tasks.add_task(_store, live_products)
                print(f"[products] Live Algolia: {len(enriched)} results for '{keyword}'")
        except Exception as e:
            print(f"[products] Algolia live call failed: {e}")

    # 3. Mock fallback only when no specific filter is applied
    if not enriched and not category_url and not category and not shop_name and not q:
        enriched = sc.generate_mock_products(keyword, count=20)
        for p in enriched:
            p["_source"] = "mock"

    # 4. Enrich with full indicators — fetch store + yesterday_reviews in parallel
    try:
        def _slug(p):
            s = p.get("shop_slug") or ""
            if not s and p.get("shop_url"):
                s = p["shop_url"].rstrip("/").split("/")[-1]
            return s

        slugs = [_slug(p) for p in enriched]
        urls  = [p.get("url", "") for p in enriched]

        async def _empty_store(): return {}

        stores, yesterdays = await asyncio.gather(
            asyncio.gather(*[db.get_store(s) if s else _empty_store() for s in slugs]),
            asyncio.gather(*[db.get_yesterday_reviews(u) for u in urls]),
        )

        enriched_full = []
        for p, store, yrev in zip(enriched, stores, yesterdays):
            try:
                enriched_full.append(enrich_product_full(p, store, yrev, enriched))
            except Exception as e2:
                print(f"[products] enrich_product_full error: {e2}")
                enriched_full.append(p)
        enriched = enriched_full
    except Exception as e:
        print(f"[products] full enrichment error: {e}")

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
async def scrape_keyword_endpoint(q: str, background_tasks: BackgroundTasks, sync: bool = False):
    if not q:
        raise HTTPException(status_code=400, detail="Keyword required")
    if sync:
        # Synchronous: run Algolia now and return results immediately
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(None, sc.scrape_keyword_sync, q, 40)
        for p in products:
            try:
                pid = await db.upsert_product(p)
                p["id"] = pid
            except Exception:
                pass
        source = "algolia" if products and not products[0].get("_source") == "mock" else "mock"
        return {"status": "done", "keyword": q, "count": len(products), "source": source, "products": products}
    background_tasks.add_task(sc.scrape_keyword, q, use_cache=False)
    return {"status": "started", "keyword": q}


@app.get("/api/scrape/categories/start")
async def scrape_categories_start(
    background_tasks: BackgroundTasks,
    delay: float = Query(1.0),
    max_pages: int = Query(1),
):
    """Start scraping via GET — accessible directly from browser."""
    return await scrape_categories_endpoint(background_tasks, delay, max_pages)


@app.post("/api/scrape/categories")
async def scrape_categories_endpoint(
    background_tasks: BackgroundTasks,
    delay: float = Query(1.0, description="Seconds between requests"),
    max_pages: int = Query(1, description="Max pages per category (1=fast, 3=full)"),
):
    """Launch a full category scrape in the background."""
    if sc._scrape_status.get("running"):
        return {"status": "already_running", **sc._scrape_status}
    async def _scrape_then_enrich():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sc.scrape_all_categories, delay, max_pages)
        # After category scrape, enrich top 300
        try:
            products = await db.get_products(limit=300)
            for p in products:
                try:
                    await db.save_review_snapshot(p.get("url", ""), p.get("reviews_total", 0))
                except Exception:
                    pass
            print("[scrape] Auto-enrich: saved review snapshots for top 300 products")
        except Exception as e:
            print(f"[scrape] auto-enrich error: {e}")

    background_tasks.add_task(_scrape_then_enrich)
    est_minutes = round(len(sc._scrape_status.get("total", 0) and [1] or [len(__import__('categories_data').TPT_LEAF_CATEGORIES) * 3 * max_pages]) * delay / 60, 1)
    return {
        "status": "started",
        "delay": delay,
        "max_pages": max_pages,
        "estimated_requests": len(__import__('categories_data').TPT_LEAF_CATEGORIES) * 3 * max_pages,
        "estimated_minutes": round(len(__import__('categories_data').TPT_LEAF_CATEGORIES) * 3 * max_pages * delay / 60, 1),
        "message": "Category scrape launched. Check /api/scrape/categories/status for progress.",
    }


@app.get("/api/scrape/categories/status")
async def scrape_categories_status():
    """Return the current status of an ongoing (or last completed) category scrape."""
    return sc._scrape_status


@app.post("/api/scrape/categories/stop")
async def scrape_categories_stop():
    """Signal the running category scrape to stop after the current request."""
    sc._scrape_status["running"] = False
    return {"status": "stop_requested"}


@app.post("/api/scrape/enrich")
async def scrape_enrich_endpoint(background_tasks: BackgroundTasks, top_n: int = 300):
    """Enrich top N products with product page + store page data."""
    async def _enrich_task(n: int):
        try:
            products = await db.get_products(limit=n)
            scraped_stores = set()
            today = datetime.now().strftime("%Y-%m-%d")
            for p in products:
                try:
                    # Save review snapshot
                    await db.save_review_snapshot(p.get("url", ""), p.get("reviews_total", 0))
                except Exception:
                    pass
                try:
                    # Scrape product page
                    product_data = await asyncio.get_event_loop().run_in_executor(
                        None, sc.scrape_product_page, p.get("url", "")
                    )
                    p.update(product_data)
                    await db.upsert_product(p)
                except Exception as e:
                    print(f"[enrich] product page error: {e}")
                # Scrape store page if not done today
                shop_slug = p.get("shop_slug") or ""
                if not shop_slug and p.get("shop_url"):
                    shop_slug = p["shop_url"].rstrip("/").split("/")[-1]
                if shop_slug and shop_slug not in scraped_stores:
                    try:
                        existing = await db.get_store(shop_slug)
                        if existing.get("scraped_at", "")[:10] != today:
                            store_data = await asyncio.get_event_loop().run_in_executor(
                                None, sc.scrape_store_page, shop_slug
                            )
                            await db.upsert_store(store_data)
                        scraped_stores.add(shop_slug)
                    except Exception as e:
                        print(f"[enrich] store page error: {e}")
            print(f"[enrich] Done enriching {len(products)} products")
        except Exception as e:
            print(f"[enrich] task error: {e}")

    background_tasks.add_task(_enrich_task, top_n)
    return {"status": "started", "top_n": top_n, "message": "Enrichment launched in background"}


_enrich_status = {"running": False, "done": 0, "total": 0, "errors": 0, "started_at": None}


async def _run_enrich_task(top_n: int = 50, len_hint: int = None):
    """Core enrichment logic — called by endpoint and auto-loop."""
    _enrich_status.update({"running": True, "done": 0, "total": 0, "errors": 0,
                            "started_at": datetime.now().isoformat()})
    try:
        products = await db.get_top_per_category(top_n=top_n)
        _enrich_status["total"] = len(products)
        scraped_stores = set()
        today = datetime.now().strftime("%Y-%m-%d")
        for p in products:
            if not _enrich_status["running"]:
                break
            try:
                product_data = await asyncio.get_event_loop().run_in_executor(
                    None, sc.fetch_product_graphql, p.get("url", "")
                )
                p.update(product_data)
                await db.upsert_product(p)
                _enrich_status["done"] += 1
            except Exception as e:
                _enrich_status["errors"] += 1
                print(f"[enrich-top] product error: {e}")
            shop_slug = p.get("shop_slug") or ""
            if not shop_slug and p.get("shop_url"):
                shop_slug = p["shop_url"].rstrip("/").split("/")[-1]
            if shop_slug and shop_slug not in scraped_stores:
                try:
                    existing = await db.get_store(shop_slug)
                    if existing.get("scraped_at", "")[:10] != today:
                        store_data = await asyncio.get_event_loop().run_in_executor(
                            None, sc.scrape_store_page, shop_slug
                        )
                        await db.upsert_store(store_data)
                    scraped_stores.add(shop_slug)
                except Exception as e:
                    print(f"[enrich-top] store error: {e}")
    except Exception as e:
        print(f"[enrich-top] task error: {e}")
    finally:
        _enrich_status["running"] = False
        print(f"[enrich-top] Done: {_enrich_status['done']}/{_enrich_status['total']}, errors={_enrich_status['errors']}")


@app.get("/api/scrape/enrich/check-dates")
async def check_dates():
    """Count products with missing date_published."""
    try:
        missing = await db.get_all_missing_date(limit=50000)
        total = await db.get_products(limit=1)
        return {
            "missing_date": len(missing),
            "message": f"{len(missing)} products still missing date_published"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/scrape/enrich/top-per-category/start")
async def enrich_top_per_category_start(background_tasks: BackgroundTasks, top_n: int = 50):
    """Scrape individual product pages for top N products per category to get age_months, description, etc."""
    if _enrich_status.get("running"):
        return {"status": "already_running", **_enrich_status}
    background_tasks.add_task(_run_enrich_task, top_n)
    return {"status": "started", "top_n": top_n,
            "message": f"Enriching top {top_n} products per category. Check /api/scrape/enrich/top-per-category/status"}


@app.get("/api/scrape/enrich/all-missing-date/start")
async def enrich_all_missing_date(background_tasks: BackgroundTasks):
    """Enrich all products with missing date_published via GraphQL."""
    if _enrich_status.get("running"):
        return {"status": "already_running", **_enrich_status}

    async def _task():
        _enrich_status.update({"running": True, "done": 0, "total": 0, "errors": 0,
                                "started_at": datetime.now().isoformat()})
        try:
            products = await db.get_all_missing_date(limit=5000)
            _enrich_status["total"] = len(products)
            for p in products:
                if not _enrich_status["running"]:
                    break
                try:
                    product_data = await asyncio.get_event_loop().run_in_executor(
                        None, sc.fetch_product_graphql, p.get("url", "")
                    )
                    p.update(product_data)
                    await db.upsert_product(p)
                    _enrich_status["done"] += 1
                except Exception as e:
                    _enrich_status["errors"] += 1
                    print(f"[enrich-date] error: {e}")
        except Exception as e:
            print(f"[enrich-date] task error: {e}")
        finally:
            _enrich_status["running"] = False
            print(f"[enrich-date] Done: {_enrich_status['done']}/{_enrich_status['total']}")

    background_tasks.add_task(_task)
    return {"status": "started", "message": "Enriching all products with missing date. Check /api/scrape/enrich/top-per-category/status"}


@app.get("/api/scrape/enrich/test-graphql")
async def test_graphql(url: str):
    """Test fetch_product_graphql on a single product URL."""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, sc.fetch_product_graphql, url
        )
        return {"status": "ok", "url": url, "data": result}
    except Exception as e:
        return {"status": "error", "url": url, "error": str(e)}


@app.get("/api/scrape/enrich/top-per-category/status")
async def enrich_top_per_category_status():
    return _enrich_status


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

@app.get("/api/debug/reset-products")
async def reset_products():
    """Truncate products table to rescrape from scratch."""
    try:
        conn = await db._pg_conn()
        await conn.execute("TRUNCATE TABLE products RESTART IDENTITY")
        await conn.close()
        return {"status": "ok", "message": "Products table cleared. Ready to rescrape."}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/category-check")
async def debug_category_check(url: str = "/browse/elementary/preschool"):
    """Check how many products exist for a specific category_url."""
    try:
        products = await db.get_products(category_url=url, limit=5)
        conn = await db._pg_conn()
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM products WHERE category_url = $1", url
        )
        await conn.close()
        return {"category_url": url, "count": count, "sample": products[:2]}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/category-urls")
async def debug_category_urls():
    """Show sample category_urls stored in DB."""
    try:
        conn = await db._pg_conn()
        rows = await conn.fetch(
            "SELECT category_url, COUNT(*) as cnt FROM products "
            "WHERE category_url IS NOT NULL AND category_url != '' "
            "GROUP BY category_url ORDER BY cnt DESC LIMIT 30"
        )
        await conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}


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

@app.get("/api/debug/tpt")
async def debug_tpt(q: str = "math"):
    """Test TPT apolloState extraction."""
    loop = asyncio.get_event_loop()
    try:
        html = await loop.run_in_executor(None, sc._fetch_tpt_search, q)
        products = sc._extract_apollo_products(html)
        return {
            "status": "success" if products else "no_products",
            "products_found": len(products),
            "sample": products[:3],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/debug/algolia")
async def debug_algolia(q: str = "math"):
    """Test TPT's Algolia API connectivity. Shows exactly what's working or not."""
    import base64
    key = sc.ALGOLIA_API_KEY
    try:
        key_decoded = base64.b64decode(key).decode()
    except Exception:
        key_decoded = "(not base64)"
    try:
        products = sc._fetch_algolia(q, count=3)
        return {
            "status": "success",
            "products_count": len(products),
            "algolia_app_id": sc.ALGOLIA_APP_ID,
            "algolia_index": sc.ALGOLIA_INDEX,
            "key_preview": key[:20] + "...",
            "key_decoded_preview": key_decoded[:60] + "...",
            "sample_product": products[0] if products else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "algolia_app_id": sc.ALGOLIA_APP_ID,
            "algolia_index": sc.ALGOLIA_INDEX,
            "key_preview": key[:20] + "...",
            "key_decoded_preview": key_decoded[:60] + "...",
            "fix": "Set TPT_ALGOLIA_KEY env var on Railway with a fresh key from Chrome DevTools → Network tab on teacherspayteachers.com",
        }

@app.get("/api/debug/scrape")
async def debug_scrape(q: str = "math"):
    import scraper as sc
    import re as _re
    url = f"https://www.teacherspayteachers.com/browse?search={q}&order=Most+Reviewed"
    try:
        html = sc._fetch_html(url)
        # Search for product-like patterns in raw HTML
        patterns = {
            "thumbnailUrl": len(_re.findall(r'thumbnailUrl', html)),
            "objectID": len(_re.findall(r'objectID', html)),
            "sellerName": len(_re.findall(r'sellerName', html)),
            "ratingCount": len(_re.findall(r'ratingCount', html)),
            "isBestSeller": len(_re.findall(r'isBestSeller', html)),
            "resourceId": len(_re.findall(r'resourceId', html)),
            "canonicalSlug": len(_re.findall(r'canonicalSlug', html)),
        }
        # Find context around first match
        sample = ""
        for key in ["thumbnailUrl", "sellerName", "canonicalSlug"]:
            m = _re.search(key, html)
            if m:
                sample = html[max(0, m.start()-100):m.start()+500]
                break
        return {
            "html_length": len(html),
            "patterns_found": patterns,
            "sample_context": sample[:800],
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/env")
async def debug_env():
    key = os.getenv("SCRAPINGBEE_API_KEY", "")
    return {
        "key_set": bool(key),
        "key_length": len(key),
        "key_preview": key[:6] + "..." if key else "EMPTY",
        "port": os.getenv("PORT", "not set"),
        "all_env_keys": sorted(os.environ.keys()),
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
