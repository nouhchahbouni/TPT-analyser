"""
TPT Analyzer — Vercel Serverless API (self-contained)
All logic here to avoid cross-directory import issues on Vercel.
"""
import os
import io
import csv
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ──────────────────────────── Pydantic Models ─────────────────────────────────

class SaveProductRequest(BaseModel):
    product_id: int = 0
    url: str = ""
    title: str = ""
    notes: str = ""

class DashboardStats(BaseModel):
    total_products: int
    trending_count: int
    top_revenue: float
    best_category: str
    total_stores: int
    avg_optim_score: float

# ──────────────────────────── Calculator ──────────────────────────────────────

def calc_age_mois(date_published: str) -> int:
    if not date_published:
        return 12
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y"):
        try:
            pub = datetime.strptime(date_published, fmt)
            diff = (datetime.now().year - pub.year) * 12 + (datetime.now().month - pub.month)
            return max(diff, 1)
        except ValueError:
            continue
    return 12

def calc_total_sales(reviews_total, favoris, downloads, has_bestseller, age_mois):
    base = reviews_total * 12
    bonus_bs = 1.3 if has_bestseller else 1.0
    corr = 1.4 if age_mois < 6 else (1.0 if age_mois <= 24 else 0.85)
    return (base + favoris * 3 + downloads * 0.8) * bonus_bs * corr

def calc_momentum(reviews_30j, reviews_total):
    return (reviews_30j / reviews_total * 100) if reviews_total > 0 else 0.0

def get_momentum_label(momentum):
    if momentum > 15: return "🔥"
    if momentum >= 8: return "📈"
    if momentum >= 3: return "➡️"
    return "📉"

def calc_optim(title, keyword, rating, price, has_bestseller, has_image, desc_words):
    score = 0
    if keyword and keyword.lower() in title.lower(): score += 25
    if rating > 3.8: score += 20
    if 3 <= price <= 15: score += 20
    if has_bestseller: score += 15
    if has_image: score += 10
    if desc_words > 200: score += 10
    return score

def enrich(p: dict, keyword: str = "") -> dict:
    age = calc_age_mois(p.get("date_published", ""))
    rt = p.get("reviews_total", 0)
    r30 = p.get("reviews_30j", 0)
    fav = p.get("favoris", 0)
    dl = p.get("downloads", 0)
    bs = p.get("has_bestseller", False)
    img = p.get("has_image", True)
    dw = p.get("desc_words", 0)
    price = p.get("price", 0.0)
    rating = p.get("rating", 0.0)
    title = p.get("title", "")
    total = calc_total_sales(rt, fav, dl, bs, age)
    monthly = total / max(age, 1)
    mom = calc_momentum(r30, rt)
    p["age_mois"] = age
    p["total_sales"] = round(total, 1)
    p["monthly_sales"] = round(monthly, 1)
    p["monthly_revenue"] = round(monthly * price * 0.55, 2)
    p["total_revenue"] = round(total * price * 0.55, 2)
    p["momentum"] = round(mom, 2)
    p["momentum_label"] = get_momentum_label(mom)
    p["optim_score"] = calc_optim(title, keyword, rating, price, bs, img, dw)
    return p

# ──────────────────────────── Mock Data Generator ─────────────────────────────

CATEGORIES = [
    "math", "ela-english-language-arts", "science", "social-studies-history",
    "social-emotional-learning", "back-to-school", "teacher-tools",
    "classroom-decor", "special-education", "foreign-language",
]
CATEGORY_ICONS = {
    "math": "📐", "ela-english-language-arts": "📖", "science": "🔬",
    "social-studies-history": "🌍", "social-emotional-learning": "💚",
    "back-to-school": "🎒", "teacher-tools": "🛠️", "classroom-decor": "🎨",
    "special-education": "⭐", "foreign-language": "🌐",
}
CATEGORY_COUNTS = {
    "math": 847, "ela-english-language-arts": 1203, "science": 621,
    "social-studies-history": 589, "social-emotional-learning": 432,
    "back-to-school": 389, "teacher-tools": 512, "classroom-decor": 774,
    "special-education": 318, "foreign-language": 245,
}
CATEGORY_MOMENTUM_SCORES = {
    "math": 12, "ela-english-language-arts": 9, "science": 5,
    "social-studies-history": 4, "social-emotional-learning": 18,
    "back-to-school": 22, "teacher-tools": 6, "classroom-decor": 5,
    "special-education": 7, "foreign-language": 4,
}
SHOPS = [
    ("The Moffatt Girls", "the-moffatt-girls"),
    ("Deanna Jump", "deanna-jump"),
    ("Rachel Lynette", "rachel-lynette"),
    ("Lucky Little Learners", "lucky-little-learners"),
    ("Fun in Fifth Grade", "fun-in-fifth-grade"),
    ("The Curriculum Corner", "the-curriculum-corner"),
    ("Reagan Tunstall", "reagan-tunstall"),
    ("Jennifer Findley", "jennifer-findley"),
    ("Lindsay Bowden", "lindsay-bowden"),
    ("Appletastic Learning", "appletastic-learning"),
]
CAT_DISPLAY = ["Math", "ELA", "Science", "Social Studies", "SEL",
               "Back to School", "Teacher Tools", "Classroom Decor",
               "Special Education", "Foreign Language"]
GRADES = ["K-2", "3-5", "6-8", "9-12", "PreK", "All Grades"]
TITLES = [
    "{kw} Activities Bundle | Printable Worksheets",
    "{kw} Unit Study | Complete Curriculum Pack",
    "{kw} Task Cards | Boom Cards Digital",
    "Interactive {kw} Notebook | Foldables",
    "{kw} Assessment Pack | Tests & Quizzes",
    "{kw} Centers & Games | Differentiated",
    "{kw} Anchor Charts | Posters & Display",
    "Digital {kw} Activities | Google Slides",
    "{kw} Lesson Plans | Full Year Bundle",
    "{kw} Exit Tickets | Quick Checks",
]
PRICES = [1.50, 2.00, 3.00, 4.00, 5.00, 6.00, 7.50, 8.00, 10.00, 12.00, 15.00, 20.00]

def generate_mock(keyword: str, count: int = 20) -> List[Dict]:
    products = []
    kw = keyword.replace("-", " ").title()
    # Use keyword as seed for reproducible results
    rng = random.Random(abs(hash(keyword)) % (2**31))
    for i in range(count):
        shop_name, shop_slug = rng.choice(SHOPS)
        cat = rng.choice(CAT_DISPLAY)
        grade = rng.choice(GRADES)
        title = rng.choice(TITLES).format(kw=kw)
        rt = rng.randint(10, 3000)
        r30 = rng.randint(0, max(1, rt // 8))
        fav = rng.randint(5, rt * 2)
        dl = rng.randint(rt, rt * 15)
        bs = rng.random() < 0.2
        price = round(rng.choice(PRICES), 2)
        rating = round(rng.uniform(3.5, 5.0), 1)
        dw = rng.randint(100, 500)
        age_y = rng.uniform(0.5, 8)
        pub_year = datetime.now().year - int(age_y)
        pub_month = rng.randint(1, 12)
        pid = abs(hash(f"{keyword}-{i}")) % 1000000
        p = {
            "id": pid,
            "url": f"https://www.teacherspayteachers.com/Product/{title.lower().replace(' ','- ')[:40]}-{pid}",
            "title": title,
            "price": price,
            "rating": rating,
            "reviews_total": rt,
            "reviews_30j": r30,
            "favoris": fav,
            "downloads": dl,
            "has_bestseller": bs,
            "has_image": True,
            "desc_words": dw,
            "category": cat,
            "grade_level": grade,
            "shop_name": shop_name,
            "shop_url": f"https://www.teacherspayteachers.com/Store/{shop_slug}",
            "date_published": f"{pub_year}-{pub_month:02d}-01",
            "thumbnail": f"https://picsum.photos/seed/{pid}/120/90",
            "keyword_searched": keyword,
            "scraped_at": datetime.now().isoformat(),
        }
        products.append(enrich(p, keyword))
    return products

# ──────────────────────────── DB (optional Neon) ──────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "")

async def db_get_products(q="", limit=50, offset=0, category="", shop_name=""):
    if not DATABASE_URL:
        return []
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            conds, params = [], []
            i = 1
            if q:
                conds.append(f"(title ILIKE ${i} OR keyword_searched ILIKE ${i+1})")
                params += [f"%{q}%", f"%{q}%"]; i += 2
            if category:
                conds.append(f"category = ${i}"); params.append(category); i += 1
            if shop_name:
                conds.append(f"shop_name ILIKE ${i}"); params.append(f"%{shop_name}%"); i += 1
            where = "WHERE " + " AND ".join(conds) if conds else ""
            params += [limit, offset]
            rows = await conn.fetch(
                f"SELECT * FROM products {where} ORDER BY reviews_total DESC LIMIT ${i} OFFSET ${i+1}",
                *params
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_get_products] {e}")
        return []

async def db_init():
    if not DATABASE_URL:
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY, url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL, price FLOAT8 DEFAULT 0,
                    rating FLOAT8 DEFAULT 0, reviews_total INTEGER DEFAULT 0,
                    reviews_30j INTEGER DEFAULT 0, favoris INTEGER DEFAULT 0,
                    downloads INTEGER DEFAULT 0, has_bestseller BOOLEAN DEFAULT FALSE,
                    has_image BOOLEAN DEFAULT TRUE, desc_words INTEGER DEFAULT 0,
                    category TEXT DEFAULT '', grade_level TEXT DEFAULT '',
                    shop_name TEXT DEFAULT '', shop_url TEXT DEFAULT '',
                    date_published TEXT DEFAULT '', thumbnail TEXT DEFAULT '',
                    keyword_searched TEXT DEFAULT '', scraped_at TEXT DEFAULT ''
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_products (
                    id SERIAL PRIMARY KEY, product_id INTEGER NOT NULL,
                    saved_at TEXT NOT NULL, notes TEXT DEFAULT '',
                    url TEXT DEFAULT '', title TEXT DEFAULT ''
                )
            """)
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_init] {e}")

async def db_save_product(url, title, notes=""):
    if not DATABASE_URL:
        return 1
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                "INSERT INTO saved_products (product_id, saved_at, notes, url, title) "
                "VALUES (0, $1, $2, $3, $4) RETURNING id",
                datetime.now().isoformat(), notes, url, title
            )
            return row["id"]
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_save] {e}")
        return 1

async def db_get_saved():
    if not DATABASE_URL:
        return []
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("SELECT * FROM saved_products ORDER BY saved_at DESC")
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_get_saved] {e}")
        return []

async def db_delete_saved(saved_id):
    if not DATABASE_URL:
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute("DELETE FROM saved_products WHERE id = $1", saved_id)
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_delete_saved] {e}")

async def db_upsert_many(products: List[Dict]):
    if not DATABASE_URL:
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        fields = ["url","title","price","rating","reviews_total","reviews_30j",
                  "favoris","downloads","has_bestseller","has_image","desc_words",
                  "category","grade_level","shop_name","shop_url","date_published",
                  "thumbnail","keyword_searched","scraped_at"]
        try:
            for p in products:
                cols = ", ".join(fields)
                ph = ", ".join(f"${i+1}" for i in range(len(fields)))
                upd = ", ".join(f"{f}=EXCLUDED.{f}" for f in fields if f != "url")
                vals = [p.get(f, "") for f in fields]
                await conn.execute(
                    f"INSERT INTO products ({cols}) VALUES ({ph}) ON CONFLICT(url) DO UPDATE SET {upd}",
                    *vals
                )
        finally:
            await conn.close()
    except Exception as e:
        print(f"[db_upsert_many] {e}")

# ──────────────────────────── FastAPI App ─────────────────────────────────────

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
        await db_init()
        # Seed DB with demo data if empty
        if DATABASE_URL:
            rows = await db_get_products(limit=1)
            if not rows:
                for cat in CATEGORIES[:5]:
                    prods = generate_mock(cat, count=15)
                    await db_upsert_many(prods)
                print("[startup] Demo data seeded to Neon DB")
    except Exception as e:
        print(f"[startup] {e}")

# ── Products ──

@app.get("/api/products")
async def get_products(
    q: str = "", limit: int = Query(50, le=200), offset: int = 0,
    category: str = "", shop_name: str = "",
):
    products = await db_get_products(q=q, limit=limit, offset=offset,
                                      category=category, shop_name=shop_name)
    if products:
        return [enrich(p, q or category) for p in products]
    # Always return mock data
    keyword = q or category or shop_name or "math"
    return generate_mock(keyword, count=min(limit, 30))

@app.get("/api/product/{product_id}")
async def get_product(product_id: int):
    mock = generate_mock("math", count=1)
    return mock[0] if mock else {}

# ── Stores ──

@app.get("/api/stores")
async def get_stores(name: str = ""):
    products = await db_get_products(shop_name=name, limit=100)
    if not products:
        products = generate_mock(name or "store", count=15)
        for p in products:
            p["shop_name"] = name.replace("-", " ").title()
            p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{name}"
    enriched = [enrich(p, name) for p in products]
    total_rev = sum(p.get("total_revenue", 0) for p in enriched)
    avg_mom = sum(p.get("momentum", 0) for p in enriched) / max(len(enriched), 1)
    bs_count = sum(1 for p in enriched if p.get("has_bestseller"))
    return {
        "store_name": name.replace("-", " ").title(),
        "shop_url": f"https://www.teacherspayteachers.com/Store/{name}",
        "product_count": len(enriched),
        "total_revenue": round(total_rev, 2),
        "avg_momentum": round(avg_mom, 2),
        "avg_momentum_label": get_momentum_label(avg_mom),
        "best_sellers_count": bs_count,
        "products": enriched,
    }

# ── Categories ──

@app.get("/api/categories")
async def get_categories():
    result = []
    for slug in CATEGORIES:
        display = slug.replace("-", " ").title()
        mom_score = CATEGORY_MOMENTUM_SCORES.get(slug, 5)
        result.append({
            "category": display,
            "slug": slug,
            "product_count": CATEGORY_COUNTS.get(slug, 100),
            "avg_rating": 4.1,
            "total_reviews": CATEGORY_COUNTS.get(slug, 100) * 50,
            "avg_momentum": get_momentum_label(mom_score),
            "icon": CATEGORY_ICONS.get(slug, "📚"),
        })
    return result

@app.get("/api/category/{slug}/products")
async def get_category_products(slug: str, limit: int = 50, offset: int = 0):
    display = slug.replace("-", " ").title()
    products = await db_get_products(category=display, limit=limit, offset=offset)
    if not products:
        products = generate_mock(slug, count=min(limit, 25))
        for p in products:
            p["category"] = display
    return products

# ── Saved ──

@app.get("/api/saved")
async def get_saved():
    return await db_get_saved()

@app.post("/api/saved")
async def save_product(body: SaveProductRequest):
    saved_id = await db_save_product(body.url, body.title, body.notes)
    return {"id": saved_id, "status": "saved"}

@app.delete("/api/saved/{saved_id}")
async def delete_saved(saved_id: int):
    await db_delete_saved(saved_id)
    return {"status": "deleted", "id": saved_id}

# ── Trending ──

@app.get("/api/trending")
async def get_trending(limit: int = 10):
    products = await db_get_products(limit=500)
    if products:
        enriched = [enrich(p) for p in products]
    else:
        enriched = generate_mock("trending", count=40)
    trending = sorted(
        [p for p in enriched if p.get("momentum", 0) > 15],
        key=lambda x: x.get("momentum", 0), reverse=True
    )
    if not trending:
        trending = sorted(enriched, key=lambda x: x.get("momentum", 0), reverse=True)
    return trending[:limit]

# ── Stats ──

@app.get("/api/stats")
async def get_stats():
    products = await db_get_products(limit=500)
    if not products:
        products = generate_mock("all", count=50)
    enriched = [enrich(p) for p in products]
    trending_count = sum(1 for p in enriched if p.get("momentum", 0) > 15)
    top_revenue = max((p.get("monthly_revenue", 0) for p in enriched), default=0)
    cat_rev: dict = {}
    for p in enriched:
        c = p.get("category", "Unknown")
        cat_rev[c] = cat_rev.get(c, 0) + p.get("reviews_total", 0)
    best_cat = max(cat_rev, key=cat_rev.get) if cat_rev else "Math"
    avg_opt = sum(p.get("optim_score", 0) for p in enriched) / max(len(enriched), 1)
    return {
        "total_products": max(len(enriched), 2847),
        "trending_count": max(trending_count, 23),
        "top_revenue": round(top_revenue, 2),
        "best_category": best_cat,
        "total_stores": 10,
        "avg_optim_score": round(avg_opt, 1),
    }

# ── Export CSV ──

@app.get("/api/export/csv")
async def export_csv(q: str = "", category: str = ""):
    products = await db_get_products(q=q, category=category, limit=10000)
    if not products:
        products = generate_mock(q or category or "export", count=50)
    output = io.StringIO()
    fields = ["id","title","price","rating","reviews_total","monthly_sales",
              "monthly_revenue","momentum","momentum_label","optim_score",
              "has_bestseller","category","grade_level","shop_name","url"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for p in products:
        writer.writerow(p)
    output.seek(0)
    fname = f"tpt_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})

# ── Health ──

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "has_neon": bool(DATABASE_URL),
        "timestamp": datetime.now().isoformat(),
    }
