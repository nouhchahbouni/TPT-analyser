"""TPT Analyzer — SQLite Database Operations"""
import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

DB_PATH = "./tpt_analyzer.db"


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                price REAL DEFAULT 0,
                rating REAL DEFAULT 0,
                reviews_total INTEGER DEFAULT 0,
                reviews_30j INTEGER DEFAULT 0,
                favoris INTEGER DEFAULT 0,
                downloads INTEGER DEFAULT 0,
                has_bestseller INTEGER DEFAULT 0,
                has_image INTEGER DEFAULT 1,
                desc_words INTEGER DEFAULT 0,
                category TEXT DEFAULT '',
                grade_level TEXT DEFAULT '',
                shop_name TEXT DEFAULT '',
                shop_url TEXT DEFAULT '',
                date_published TEXT DEFAULT '',
                thumbnail TEXT DEFAULT '',
                keyword_searched TEXT DEFAULT '',
                scraped_at TEXT DEFAULT ''
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                saved_at TEXT NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scrape_cache (
                keyword TEXT PRIMARY KEY,
                scraped_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def upsert_product(product: Dict[str, Any]) -> int:
    """Insert or update a product. Returns the product id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Check if exists
        async with db.execute("SELECT id FROM products WHERE url = ?", (product["url"],)) as cursor:
            row = await cursor.fetchone()

        fields = ["url", "title", "price", "rating", "reviews_total", "reviews_30j",
                  "favoris", "downloads", "has_bestseller", "has_image", "desc_words",
                  "category", "grade_level", "shop_name", "shop_url", "date_published",
                  "thumbnail", "keyword_searched", "scraped_at"]

        if row:
            product_id = row["id"]
            set_clause = ", ".join(f"{f} = ?" for f in fields if f != "url")
            values = [product.get(f, "") for f in fields if f != "url"]
            values.append(product_id)
            await db.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
        else:
            placeholders = ", ".join("?" for _ in fields)
            cols = ", ".join(fields)
            values = [product.get(f, "") for f in fields]
            await db.execute(f"INSERT INTO products ({cols}) VALUES ({placeholders})", values)
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                result = await cursor.fetchone()
                product_id = result[0]

        await db.commit()
        return product_id


async def get_products(q: str = "", limit: int = 50, offset: int = 0,
                       category: str = "", shop_name: str = "") -> List[Dict]:
    """Fetch products with optional filters."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []

        if q:
            conditions.append("(title LIKE ? OR keyword_searched LIKE ? OR shop_name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        if category:
            conditions.append("category = ?")
            params.append(category)
        if shop_name:
            conditions.append("shop_name LIKE ?")
            params.append(f"%{shop_name}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])

        async with db.execute(
            f"SELECT * FROM products {where} ORDER BY reviews_total DESC LIMIT ? OFFSET ?",
            params
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_product_by_id(product_id: int) -> Optional[Dict]:
    """Fetch a single product by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_categories() -> List[Dict]:
    """Get distinct categories with product counts."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT category, COUNT(*) as product_count,
                   AVG(rating) as avg_rating,
                   SUM(reviews_total) as total_reviews
            FROM products
            WHERE category != ''
            GROUP BY category
            ORDER BY product_count DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_saved_products() -> List[Dict]:
    """Fetch all saved products with product details."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sp.id as saved_id, sp.saved_at, sp.notes,
                   p.*
            FROM saved_products sp
            JOIN products p ON p.id = sp.product_id
            ORDER BY sp.saved_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def save_product(product_id: int, notes: str = "") -> int:
    """Save a product to saved list."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO saved_products (product_id, saved_at, notes) VALUES (?, ?, ?)",
            (product_id, now, notes)
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            result = await cursor.fetchone()
            return result[0]


async def delete_saved_product(saved_id: int) -> bool:
    """Remove a product from saved list."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM saved_products WHERE id = ?", (saved_id,))
        await db.commit()
        return True


async def get_db_stats() -> Dict:
    """Get overall database statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) as total FROM products") as c:
            total = (await c.fetchone())["total"]
        async with db.execute("SELECT COUNT(DISTINCT shop_name) as stores FROM products WHERE shop_name != ''") as c:
            stores = (await c.fetchone())["stores"]
        async with db.execute("SELECT AVG(rating) as avg_rating FROM products WHERE rating > 0") as c:
            avg_rating = (await c.fetchone())["avg_rating"] or 0
        return {"total_products": total, "total_stores": stores, "avg_rating": round(avg_rating, 2)}


async def is_cache_valid(keyword: str) -> bool:
    """Check if scrape cache is still valid (24h)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expires_at FROM scrape_cache WHERE keyword = ?", (keyword,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            expires_at = datetime.fromisoformat(row[0])
            return datetime.now() < expires_at


async def set_cache(keyword: str):
    """Set scrape cache entry with 24h expiry."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now()
        expires = now + timedelta(hours=24)
        await db.execute(
            "INSERT OR REPLACE INTO scrape_cache (keyword, scraped_at, expires_at) VALUES (?, ?, ?)",
            (keyword, now.isoformat(), expires.isoformat())
        )
        await db.commit()
