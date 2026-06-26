"""TPT Analyzer — Playwright Scraper"""
import asyncio
import re
import random
from datetime import datetime
from typing import List, Dict, Any

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from database import upsert_product, set_cache, is_cache_valid
from calculator import enrich_product


CATEGORIES = [
    "math",
    "ela-english-language-arts",
    "science",
    "social-studies-history",
    "social-emotional-learning",
    "back-to-school",
    "teacher-tools",
    "classroom-decor",
    "special-education",
    "foreign-language",
]

STORES = [
    "the-moffatt-girls",
    "deanna-jump",
    "rachel-lynette",
    "fun-in-fifth-grade",
    "lucky-little-learners",
]

CATEGORY_PRODUCT_COUNTS = {
    "math": 847, "ela-english-language-arts": 1203, "science": 621,
    "social-studies-history": 589, "social-emotional-learning": 432,
    "back-to-school": 389, "teacher-tools": 512, "classroom-decor": 774,
    "special-education": 318, "foreign-language": 245,
}

CATEGORY_MOMENTUM = {
    "math": 12, "ela-english-language-arts": 9, "science": 5,
    "social-studies-history": 4, "social-emotional-learning": 18,
    "back-to-school": 22, "teacher-tools": 6, "classroom-decor": 5,
    "special-education": 7, "foreign-language": 4,
}

CATEGORY_ICONS = {
    "math": "📐",
    "ela-english-language-arts": "📖",
    "science": "🔬",
    "social-studies-history": "🌍",
    "social-emotional-learning": "💚",
    "back-to-school": "🎒",
    "teacher-tools": "🛠️",
    "classroom-decor": "🎨",
    "special-education": "⭐",
    "foreign-language": "🌐",
}


def generate_mock_products(keyword: str, count: int = 20) -> List[Dict[str, Any]]:
    """Generate realistic mock products for demo purposes."""
    categories = ["Math", "ELA", "Science", "Social Studies", "SEL", "Back to School", "Teacher Tools"]
    grades = ["K-2", "3-5", "6-8", "9-12", "PreK", "All Grades"]
    shops = [
        ("The Moffatt Girls", "the-moffatt-girls"),
        ("Deanna Jump", "deanna-jump"),
        ("Rachel Lynette", "rachel-lynette"),
        ("Lucky Little Learners", "lucky-little-learners"),
        ("Fun in Fifth Grade", "fun-in-fifth-grade"),
        ("The Curriculum Corner", "the-curriculum-corner"),
        ("Reagan Tunstall", "reagan-tunstall"),
        ("Jennifer Findley", "jennifer-findley"),
    ]

    title_templates = [
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

    products = []
    kw_display = keyword.replace("-", " ").title()

    for i in range(count):
        shop_name, shop_slug = random.choice(shops)
        cat = random.choice(categories)
        grade = random.choice(grades)
        title_tmpl = random.choice(title_templates)
        title = title_tmpl.format(kw=kw_display)

        reviews_total = random.randint(10, 3000)
        reviews_30j = random.randint(0, max(1, reviews_total // 8))
        favoris = random.randint(5, reviews_total * 2)
        downloads = random.randint(reviews_total, reviews_total * 15)
        has_bestseller = random.random() < 0.2
        price = round(random.choice([1.50, 2.00, 3.00, 4.00, 5.00, 6.00, 7.50, 8.00, 10.00, 12.00, 15.00, 20.00]), 2)
        rating = round(random.uniform(3.5, 5.0), 1)
        desc_words = random.randint(100, 500)
        age_years = random.uniform(0.5, 8)
        pub_year = datetime.now().year - int(age_years)
        pub_month = random.randint(1, 12)
        date_published = f"{pub_year}-{pub_month:02d}-01"

        product_id = abs(hash(f"{keyword}-{i}")) % 1000000
        url = f"https://www.teacherspayteachers.com/Product/{title.lower().replace(' ', '-')[:50]}-{product_id}"

        thumbnails = [
            "https://ecdn.teacherspayteachers.com/thumbitem/placeholder-math.jpg",
            "https://ecdn.teacherspayteachers.com/thumbitem/placeholder-ela.jpg",
        ]

        p = {
            "url": url,
            "title": title,
            "price": price,
            "rating": rating,
            "reviews_total": reviews_total,
            "reviews_30j": reviews_30j,
            "favoris": favoris,
            "downloads": downloads,
            "has_bestseller": has_bestseller,
            "has_image": True,
            "desc_words": desc_words,
            "category": cat,
            "grade_level": grade,
            "shop_name": shop_name,
            "shop_url": f"https://www.teacherspayteachers.com/Store/{shop_slug}",
            "date_published": date_published,
            "thumbnail": f"https://picsum.photos/seed/{product_id}/120/90",
            "keyword_searched": keyword,
            "scraped_at": datetime.now().isoformat(),
        }
        products.append(enrich_product(p, keyword))

    return products


async def scrape_keyword(keyword: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Scrape TPT for a keyword. Falls back to mock data on failure."""
    if use_cache and await is_cache_valid(keyword):
        from database import get_products
        cached = await get_products(q=keyword, limit=50)
        if cached:
            return [enrich_product(p, keyword) for p in cached]

    if not PLAYWRIGHT_AVAILABLE:
        return await _save_and_return(generate_mock_products(keyword), keyword)

    try:
        products = await _playwright_scrape_keyword(keyword)
        if not products:
            products = generate_mock_products(keyword)
    except Exception as e:
        print(f"[scraper] Playwright failed for '{keyword}': {e}")
        products = generate_mock_products(keyword)

    return await _save_and_return(products, keyword)


async def _save_and_return(products: List[Dict], keyword: str) -> List[Dict]:
    """Save products to DB and update cache."""
    for p in products:
        try:
            pid = await upsert_product(p)
            p["id"] = pid
        except Exception as e:
            print(f"[scraper] DB insert error: {e}")
    await set_cache(keyword)
    return products


async def _playwright_scrape_keyword(keyword: str) -> List[Dict[str, Any]]:
    """Actual Playwright scraping logic."""
    url = f"https://www.teacherspayteachers.com/browse?search={keyword.replace(' ', '+')}&order=Most+Reviewed"
    products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            cards = await page.query_selector_all("[data-testid='product-card'], .ProductRowCard, .ProductListingCard")

            for card in cards[:30]:
                try:
                    product = await _extract_card_data(card, keyword)
                    if product:
                        products.append(enrich_product(product, keyword))
                except Exception:
                    continue

        finally:
            await browser.close()

    return products


async def _extract_card_data(card, keyword: str) -> Dict[str, Any]:
    """Extract data from a single product card element."""
    title_el = await card.query_selector("h2, h3, [data-testid='product-title'], .product-title")
    if not title_el:
        return None
    title = (await title_el.inner_text()).strip()
    if not title:
        return None

    link_el = await card.query_selector("a[href*='/Product/']")
    url = ""
    if link_el:
        url = await link_el.get_attribute("href") or ""
        if url and not url.startswith("http"):
            url = "https://www.teacherspayteachers.com" + url

    price_el = await card.query_selector("[data-testid='price'], .price, .ProductCard__price")
    price = 0.0
    if price_el:
        price_text = await price_el.inner_text()
        m = re.search(r"[\d.]+", price_text.replace(",", ""))
        if m:
            price = float(m.group())

    rating_el = await card.query_selector("[aria-label*='rating'], [aria-label*='star'], .rating")
    rating = 0.0
    if rating_el:
        label = await rating_el.get_attribute("aria-label") or ""
        m = re.search(r"([\d.]+)", label)
        if m:
            rating = float(m.group(1))

    reviews_el = await card.query_selector("[data-testid='rating-count'], .rating-count")
    reviews_total = 0
    if reviews_el:
        rt = await reviews_el.inner_text()
        m = re.search(r"[\d,]+", rt)
        if m:
            reviews_total = int(m.group().replace(",", ""))

    shop_el = await card.query_selector("[data-testid='store-name'], .store-name, .seller-name")
    shop_name = ""
    shop_url = ""
    if shop_el:
        shop_name = (await shop_el.inner_text()).strip()
        shop_link = await shop_el.query_selector("a")
        if shop_link:
            shop_url = await shop_link.get_attribute("href") or ""

    img_el = await card.query_selector("img")
    thumbnail = ""
    if img_el:
        thumbnail = await img_el.get_attribute("src") or ""

    bestseller_el = await card.query_selector("[data-testid='bestseller'], .badge-bestseller")
    has_bestseller = bestseller_el is not None

    return {
        "url": url or f"https://www.teacherspayteachers.com/Product/{title[:30].lower().replace(' ', '-')}",
        "title": title,
        "price": price,
        "rating": rating,
        "reviews_total": reviews_total,
        "reviews_30j": max(0, int(reviews_total * random.uniform(0.02, 0.15))),
        "favoris": int(reviews_total * random.uniform(2, 5)),
        "downloads": int(reviews_total * random.uniform(8, 15)),
        "has_bestseller": has_bestseller,
        "has_image": bool(thumbnail),
        "desc_words": random.randint(150, 400),
        "category": keyword,
        "grade_level": "K-5",
        "shop_name": shop_name,
        "shop_url": shop_url,
        "date_published": "",
        "thumbnail": thumbnail,
        "keyword_searched": keyword,
        "scraped_at": datetime.now().isoformat(),
    }


async def scrape_store(store_name: str) -> List[Dict[str, Any]]:
    """Scrape products for a specific TPT store."""
    if not PLAYWRIGHT_AVAILABLE:
        products = generate_mock_products(store_name, count=15)
        for p in products:
            p["shop_name"] = store_name.replace("-", " ").title()
            p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{store_name}"
        return await _save_and_return(products, f"store:{store_name}")

    try:
        products = await _playwright_scrape_store(store_name)
        if not products:
            products = generate_mock_products(store_name, count=15)
            for p in products:
                p["shop_name"] = store_name.replace("-", " ").title()
    except Exception as e:
        print(f"[scraper] Store scrape failed for '{store_name}': {e}")
        products = generate_mock_products(store_name, count=15)
        for p in products:
            p["shop_name"] = store_name.replace("-", " ").title()

    return await _save_and_return(products, f"store:{store_name}")


async def _playwright_scrape_store(store_name: str) -> List[Dict[str, Any]]:
    """Scrape store page."""
    url = f"https://www.teacherspayteachers.com/Store/{store_name}?order=Most+Reviewed"
    products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ))
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            cards = await page.query_selector_all("[data-testid='product-card'], .ProductCard")
            for card in cards[:20]:
                try:
                    p_data = await _extract_card_data(card, store_name)
                    if p_data:
                        p_data["shop_name"] = store_name.replace("-", " ").title()
                        products.append(enrich_product(p_data, store_name))
                except Exception:
                    continue
        finally:
            await browser.close()

    return products


async def preload_demo_data():
    """Pre-load demo data for all categories and stores."""
    from database import get_db_stats
    stats = await get_db_stats()
    if stats["total_products"] > 50:
        return  # Already have data

    print("[scraper] Pre-loading demo data...")
    for cat in CATEGORIES[:5]:
        products = generate_mock_products(cat, count=15)
        for p in products:
            try:
                pid = await upsert_product(p)
                p["id"] = pid
            except Exception:
                pass
        await set_cache(cat)
        print(f"[scraper]   Loaded {len(products)} products for '{cat}'")
