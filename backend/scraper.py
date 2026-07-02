"""TPT Analyzer — ScrapingBee Scraper"""
import os
import re
import json
import random
import asyncio
import requests
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from calculator import enrich_product

SCRAPINGBEE_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")
SCRAPINGBEE_URL = "https://app.scrapingbee.com/api/v1/"

# TPT uses Algolia for search — these are TPT's client-side (read-only) credentials.
# Set TPT_ALGOLIA_KEY env var on Railway to override when this key expires.
ALGOLIA_APP_ID = os.getenv("TPT_ALGOLIA_APP_ID", "FNSE9IYL6S")
ALGOLIA_API_KEY = os.getenv(
    "TPT_ALGOLIA_KEY",
    "YWQzNjM4ZTk0OGZlMzVlMTVlZWVkMzFiZDkwNGE5OTQ4NDI1ODQ5ZWQzZWZiMzQ5ZGUxNjQ3YTQwMWYzYjg1M2ZpbHRlcnM9JTI4aXNGcmVlJTNBZmFsc2UlMjklMjBBTkQlMjAlMjhpc0FwcHJvdmVkJTNBdHJ1ZSUyOQ=="
)
ALGOLIA_INDEX = os.getenv("TPT_ALGOLIA_INDEX", "production_resources")

CATEGORIES = [
    "math", "ela-english-language-arts", "science",
    "social-studies-history", "social-emotional-learning",
    "back-to-school", "teacher-tools", "classroom-decor",
    "special-education", "foreign-language",
]
STORES = [
    "the-moffatt-girls", "deanna-jump", "rachel-lynette",
    "fun-in-fifth-grade", "lucky-little-learners",
    "lindsay-bowden", "appletastic-learning",
    "the-stellar-teacher-company",
]
CATEGORY_ICONS = {
    "math": "📐", "ela-english-language-arts": "📖", "science": "🔬",
    "social-studies-history": "🌍", "social-emotional-learning": "💚",
    "back-to-school": "🎒", "teacher-tools": "🛠️", "classroom-decor": "🎨",
    "special-education": "⭐", "foreign-language": "🌐",
}
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


# ──────────────────────────────────────────────────────────────────────────────
# ScrapingBee fetch
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> str:
    """Fetch a URL via ScrapingBee and return raw HTML."""
    if not SCRAPINGBEE_KEY:
        raise RuntimeError("SCRAPINGBEE_API_KEY not set")
    resp = requests.get(
        SCRAPINGBEE_URL,
        params={
            "api_key": SCRAPINGBEE_KEY,
            "url": url,
            "render_js": "true",
            "wait": "8000",
            "block_ads": "true",
            "block_resources": "false",
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.text


# ──────────────────────────────────────────────────────────────────────────────
# TPT HTML parser
# ──────────────────────────────────────────────────────────────────────────────

def _parse_price(text: str) -> float:
    m = re.search(r"[\d]+\.[\d]{2}|[\d]+", (text or "").replace(",", ""))
    return float(m.group()) if m else 0.0

def _parse_int(text: str) -> int:
    m = re.search(r"[\d,]+", (text or "").replace(",", ""))
    return int(m.group().replace(",", "")) if m else 0

def _parse_rating(text: str) -> float:
    m = re.search(r"([\d.]+)\s*out\s*of\s*[\d.]+|([\d.]+)\s*star", (text or ""), re.I)
    if m:
        return float(m.group(1) or m.group(2))
    m = re.search(r"[\d.]+", text or "")
    return float(m.group()) if m else 0.0

def _extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """Try to extract product data from JSON-LD schema markup."""
    products = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("Product", "ItemList"):
                    if item.get("@type") == "ItemList":
                        for el in item.get("itemListElement", []):
                            p = el.get("item", el)
                            products.append(_normalize_jsonld(p))
                    else:
                        products.append(_normalize_jsonld(item))
        except Exception:
            continue
    return [p for p in products if p.get("title")]

def _normalize_jsonld(item: dict) -> dict:
    offer = item.get("offers", {})
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    agg = item.get("aggregateRating", {})
    return {
        "title": item.get("name", ""),
        "url": item.get("url", ""),
        "price": _parse_price(str(offer.get("price", "0"))),
        "rating": float(agg.get("ratingValue", 0)),
        "reviews_total": int(agg.get("reviewCount", 0)),
        "thumbnail": (item.get("image", [""])[0] if isinstance(item.get("image"), list)
                      else item.get("image", "")),
        "has_bestseller": False,
        "has_image": bool(item.get("image")),
    }

def _extract_next_data(soup: BeautifulSoup) -> List[Dict]:
    """Extract products from Next.js __NEXT_DATA__ JSON embedded in TPT pages."""
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return []
    try:
        data = json.loads(tag.string)
        # Navigate into the Next.js page props
        props = data.get("props", {}).get("pageProps", {})
        # Try common TPT data keys
        resources = (
            props.get("resources") or
            props.get("products") or
            props.get("searchResults", {}).get("resources") or
            props.get("searchResults", {}).get("data") or
            props.get("initialData", {}).get("resources") or
            []
        )
        if not resources and "dehydratedState" in props:
            # React Query dehydrated state
            queries = props["dehydratedState"].get("queries", [])
            for q in queries:
                qdata = q.get("state", {}).get("data", {})
                resources = (qdata.get("resources") or qdata.get("products") or
                             qdata.get("data", {}).get("resources") or [])
                if resources:
                    break
        products = []
        for r in resources:
            if not isinstance(r, dict):
                continue
            name = r.get("name") or r.get("title") or r.get("resourceTitle") or ""
            if not name:
                continue
            rid = r.get("id") or r.get("resourceId") or ""
            url = r.get("url") or (f"https://www.teacherspayteachers.com/Product/{rid}" if rid else "")
            price_raw = r.get("price") or r.get("priceInCents", 0)
            price = float(price_raw) / 100 if isinstance(price_raw, int) and price_raw > 100 else float(price_raw or 0)
            rating = float(r.get("rating") or r.get("averageRating") or 0)
            reviews = int(r.get("ratingCount") or r.get("reviewCount") or r.get("totalRatings") or 0)
            shop = r.get("sellerName") or r.get("storeName") or r.get("seller", {}).get("name") or ""
            shop_url_slug = r.get("storeUrlName") or r.get("seller", {}).get("urlName") or ""
            thumb = (r.get("thumbnailUrl") or r.get("previewImages", [{}])[0].get("url") if r.get("previewImages") else "") or ""
            bs = bool(r.get("isBestSeller") or r.get("bestSeller"))
            products.append({
                "title": str(name)[:200],
                "url": url if url.startswith("http") else f"https://www.teacherspayteachers.com{url}",
                "price": price,
                "rating": rating,
                "reviews_total": reviews,
                "thumbnail": thumb,
                "shop_name": shop,
                "shop_url": f"https://www.teacherspayteachers.com/Store/{shop_url_slug}" if shop_url_slug else "",
                "has_bestseller": bs,
                "has_image": bool(thumb),
            })
        return products
    except Exception as e:
        print(f"[scraper] __NEXT_DATA__ parse error: {e}")
        return []


def _extract_tpt_state(soup: BeautifulSoup) -> List[Dict]:
    """Extract products from TPT's inline var state = {...} JavaScript object."""
    products = []
    for script in soup.find_all("script"):
        text = script.string or ""
        if "var state" not in text and "window.state" not in text:
            continue
        # Extract the state JSON object
        m = re.search(r'var state\s*=\s*(\{.+\})\s*;?\s*(?:var|window|$)', text, re.DOTALL)
        if not m:
            m = re.search(r'var state\s*=\s*(\{.+)', text, re.DOTALL)
        if not m:
            continue
        raw = m.group(1).strip().rstrip(';')
        # Try to find matching brace
        depth = 0
        end = 0
        for i, ch in enumerate(raw):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end:
            raw = raw[:end]
        try:
            state = json.loads(raw)
        except Exception:
            # Try to find product-like structures with regex
            resource_blocks = re.findall(
                r'\{[^{}]*"(?:name|title)":\s*"([^"]{5,})"[^{}]*"price":\s*([\d.]+)[^{}]*\}',
                text
            )
            for name, price in resource_blocks[:30]:
                products.append({
                    "title": name[:200],
                    "url": "",
                    "price": float(price),
                    "rating": 0.0,
                    "reviews_total": 0,
                    "thumbnail": "",
                    "shop_name": "",
                    "has_bestseller": False,
                    "has_image": False,
                })
            continue

        # Navigate through state to find resources/products
        def find_resources(obj, depth=0):
            if depth > 6 or not isinstance(obj, dict):
                return []
            for key in ("resources", "products", "searchResults", "items", "data"):
                if key in obj and isinstance(obj[key], list) and len(obj[key]) > 0:
                    arr = obj[key]
                    if isinstance(arr[0], dict) and ("name" in arr[0] or "title" in arr[0]):
                        return arr
            for v in obj.values():
                if isinstance(v, dict):
                    result = find_resources(v, depth + 1)
                    if result:
                        return result
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    if "name" in v[0] or "title" in v[0]:
                        return v
            return []

        resources = find_resources(state)
        for r in resources:
            name = r.get("name") or r.get("title") or r.get("resourceTitle") or ""
            if not name:
                continue
            rid = r.get("id") or r.get("resourceId") or ""
            url = r.get("url") or (f"https://www.teacherspayteachers.com/Product/{rid}" if rid else "")
            price_raw = r.get("price") or r.get("priceInCents", 0)
            price = float(price_raw) / 100 if isinstance(price_raw, int) and price_raw > 100 else float(price_raw or 0)
            products.append({
                "title": str(name)[:200],
                "url": url if str(url).startswith("http") else f"https://www.teacherspayteachers.com{url}",
                "price": price,
                "rating": float(r.get("rating") or r.get("averageRating") or 0),
                "reviews_total": int(r.get("ratingCount") or r.get("reviewCount") or 0),
                "thumbnail": r.get("thumbnailUrl") or r.get("previewUrl") or "",
                "shop_name": r.get("sellerName") or r.get("storeName") or "",
                "shop_url": f"https://www.teacherspayteachers.com/Store/{r.get('storeUrlName', '')}",
                "has_bestseller": bool(r.get("isBestSeller")),
                "has_image": bool(r.get("thumbnailUrl")),
            })
        if products:
            break
    return products


def _extract_inline_json(soup: BeautifulSoup) -> List[Dict]:
    """Search all inline scripts for product arrays."""
    products = []
    for script in soup.find_all("script"):
        text = script.string or ""
        if not text or len(text) < 100:
            continue
        # Look for JSON blobs containing product arrays
        matches = re.findall(r'\{[^{}]*"(?:name|title)"[^{}]*"(?:price|rating)"[^{}]*\}', text)
        for m in matches:
            try:
                obj = json.loads(m)
                name = obj.get("name") or obj.get("title") or ""
                if name:
                    products.append({
                        "title": str(name)[:200],
                        "url": obj.get("url", ""),
                        "price": float(obj.get("price", 0)),
                        "rating": float(obj.get("rating", 0)),
                        "reviews_total": int(obj.get("reviewCount", 0)),
                        "thumbnail": obj.get("image", ""),
                        "shop_name": obj.get("brand", {}).get("name", "") if isinstance(obj.get("brand"), dict) else "",
                        "has_bestseller": False,
                        "has_image": bool(obj.get("image")),
                    })
            except Exception:
                continue
        # Also try larger JSON blobs with arrays
        if not products:
            for match in re.finditer(r'"resources"\s*:\s*(\[[^\]]{200,}\])', text):
                try:
                    arr = json.loads(match.group(1))
                    for item in arr:
                        if isinstance(item, dict) and (item.get("name") or item.get("title")):
                            name = item.get("name") or item.get("title", "")
                            products.append({
                                "title": str(name)[:200],
                                "url": item.get("url", ""),
                                "price": float(item.get("price", 0)),
                                "rating": float(item.get("rating", 0)),
                                "reviews_total": int(item.get("ratingCount", 0)),
                                "thumbnail": item.get("thumbnailUrl", ""),
                                "shop_name": item.get("sellerName", ""),
                                "has_bestseller": bool(item.get("isBestSeller")),
                                "has_image": bool(item.get("thumbnailUrl")),
                            })
                except Exception:
                    continue
    return products


def _parse_search_page(html: str, keyword: str) -> List[Dict]:
    """Parse TPT search results page HTML → list of product dicts."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Try TPT's inline var state = {...}
    products = _extract_tpt_state(soup)
    if products:
        print(f"[scraper] ✅ Extracted {len(products)} products from TPT state")
        return _finalize(products, keyword)

    # 2. Try __NEXT_DATA__ (most reliable — server-side rendered JSON)
    products = _extract_next_data(soup)
    if products:
        print(f"[scraper] ✅ Extracted {len(products)} products from __NEXT_DATA__")
        return _finalize(products, keyword)

    # 2. Try JSON-LD schema markup
    products = _extract_json_ld(soup)
    if products:
        print(f"[scraper] ✅ Extracted {len(products)} products from JSON-LD")
        return _finalize(products, keyword)

    # 3. Try inline JS JSON blobs
    products = _extract_inline_json(soup)
    if products:
        print(f"[scraper] ✅ Extracted {len(products)} products from inline JS")
        return _finalize(products, keyword)

    # 3. Fallback: parse product cards from HTML
    cards = (
        soup.select("[data-testid='product-card']") or
        soup.select(".ProductRowCard") or
        soup.select("[class*='ProductCard']") or
        soup.select("li[class*='product']") or
        soup.select("article[class*='product']")
    )

    for card in cards[:30]:
        try:
            link = card.find("a", href=re.compile(r"/Product/"))
            if not link:
                continue
            title = link.get_text(strip=True) or link.get("title", "")
            url = link.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.teacherspayteachers.com" + url
            price_el = (card.find(attrs={"data-testid": "price"}) or
                        card.find(class_=re.compile(r"[Pp]rice")))
            price = _parse_price(price_el.get_text() if price_el else "")
            rating_el = card.find(attrs={"aria-label": re.compile(r"star|rating", re.I)})
            rating = _parse_rating(rating_el.get("aria-label", "") if rating_el else "")
            review_el = (card.find(attrs={"data-testid": "rating-count"}) or
                         card.find(class_=re.compile(r"[Rr]ating[Cc]ount|[Rr]eview")))
            reviews = _parse_int(review_el.get_text() if review_el else "")
            shop_el = (card.find(attrs={"data-testid": "store-name"}) or
                       card.find(class_=re.compile(r"[Ss]tore|[Ss]eller|[Ss]hop")))
            shop_name = shop_el.get_text(strip=True) if shop_el else ""
            img = card.find("img")
            thumbnail = (img.get("src") or img.get("data-src") or "") if img else ""
            bs = bool(card.find(class_=re.compile(r"[Bb]est[Ss]eller|[Bb]adge")))
            if not title:
                continue
            products.append({
                "title": title[:200],
                "url": url,
                "price": price,
                "rating": rating,
                "reviews_total": reviews,
                "thumbnail": thumbnail,
                "shop_name": shop_name,
                "has_bestseller": bs,
                "has_image": bool(thumbnail),
            })
        except Exception:
            continue

    if products:
        print(f"[scraper] ✅ Extracted {len(products)} products from HTML cards")
    return _finalize(products, keyword)

def _finalize(products: List[Dict], keyword: str) -> List[Dict]:
    """Add missing fields + enrich with calculated scores."""
    result = []
    for p in products:
        if not p.get("title"):
            continue
        p.setdefault("reviews_30j", max(0, int(p.get("reviews_total", 0) * random.uniform(0.03, 0.18))))
        p.setdefault("favoris", int(p.get("reviews_total", 0) * random.uniform(1.5, 4)))
        p.setdefault("downloads", int(p.get("reviews_total", 0) * random.uniform(8, 15)))
        p.setdefault("desc_words", random.randint(150, 400))
        p.setdefault("category", keyword.replace("-", " ").title())
        p.setdefault("grade_level", "K-5")
        p.setdefault("shop_url", "")
        p.setdefault("date_published", "")
        p.setdefault("thumbnail", "")
        p.setdefault("shop_name", "")
        p["keyword_searched"] = keyword
        p["scraped_at"] = datetime.now().isoformat()
        result.append(enrich_product(p, keyword))
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Public scrape functions
# ──────────────────────────────────────────────────────────────────────────────

JS_EXTRACT = """
(function() {
    function findProducts(obj, depth) {
        if (depth > 8 || !obj || typeof obj !== 'object') return null;
        var keys = Object.keys(obj);
        for (var i = 0; i < keys.length; i++) {
            var val = obj[keys[i]];
            if (Array.isArray(val) && val.length > 2) {
                var first = val[0];
                if (first && typeof first === 'object' && (first.name || first.title || first.resourceTitle)) {
                    return val;
                }
            }
            if (val && typeof val === 'object' && !Array.isArray(val)) {
                var found = findProducts(val, depth + 1);
                if (found) return found;
            }
        }
        return null;
    }
    var sources = [window, window.__store__, window.__REDUX_STORE__, window.App];
    for (var s = 0; s < sources.length; s++) {
        try {
            var products = findProducts(sources[s], 0);
            if (products && products.length > 0) return JSON.stringify(products.slice(0, 40));
        } catch(e) {}
    }
    return JSON.stringify([]);
})()
"""

def _fetch_tpt_js(keyword: str) -> List[Dict]:
    """Use ScrapingBee JS snippet to extract products from TPT's JS state after page load."""
    import base64
    if not SCRAPINGBEE_KEY:
        raise RuntimeError("SCRAPINGBEE_API_KEY not set")
    url = f"https://www.teacherspayteachers.com/browse?search={requests.utils.quote(keyword)}&order=Most+Reviewed"
    js_b64 = base64.b64encode(JS_EXTRACT.encode()).decode()
    resp = requests.get(
        SCRAPINGBEE_URL,
        params={
            "api_key": SCRAPINGBEE_KEY,
            "url": url,
            "render_js": "true",
            "wait": "6000",
            "js_snippet": js_b64,
        },
        timeout=90,
    )
    resp.raise_for_status()
    # ScrapingBee returns JS snippet result in response body when js_snippet is used
    try:
        raw = resp.json()
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("result") or raw.get("data") or []
        else:
            items = json.loads(resp.text)
    except Exception:
        try:
            items = json.loads(resp.text)
        except Exception:
            return []

    if not isinstance(items, list):
        return []

    products = []
    for r in items:
        if not isinstance(r, dict):
            continue
        name = r.get("name") or r.get("title") or r.get("resourceTitle") or ""
        if not name:
            continue
        rid = r.get("id") or r.get("resourceId") or ""
        url_p = r.get("url") or (f"https://www.teacherspayteachers.com/Product/{rid}" if rid else "")
        price_raw = r.get("price") or r.get("priceInCents", 0)
        price = float(price_raw) / 100 if isinstance(price_raw, int) and price_raw > 100 else float(price_raw or 0)
        products.append({
            "title": str(name)[:200],
            "url": url_p if str(url_p).startswith("http") else f"https://www.teacherspayteachers.com{url_p}",
            "price": price,
            "rating": float(r.get("rating") or r.get("averageRating") or 0),
            "reviews_total": int(r.get("ratingCount") or r.get("reviewCount") or 0),
            "thumbnail": r.get("thumbnailUrl") or r.get("previewUrl") or "",
            "shop_name": r.get("sellerName") or r.get("storeName") or "",
            "shop_url": f"https://www.teacherspayteachers.com/Store/{r.get('storeUrlName', '')}",
            "has_bestseller": bool(r.get("isBestSeller")),
            "has_image": bool(r.get("thumbnailUrl")),
        })
    return products


def _fetch_tpt_search(keyword: str) -> str:
    """Fetch TPT search page HTML. Tries direct request first, falls back to ScrapingBee."""
    url = f"https://www.teacherspayteachers.com/browse?search={requests.utils.quote(keyword)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and "apolloState" in resp.text:
            print(f"[scraper] ✅ Direct TPT fetch succeeded for '{keyword}'")
            return resp.text
        print(f"[scraper] Direct fetch status={resp.status_code}, len={len(resp.text)}, has_apollo={'apolloState' in resp.text}")
    except Exception as e:
        print(f"[scraper] Direct fetch failed: {e}")

    if not SCRAPINGBEE_KEY:
        raise RuntimeError("TPT fetch blocked by Cloudflare and SCRAPINGBEE_API_KEY not set")

    try:
        resp = requests.get(
            SCRAPINGBEE_URL,
            params={
                "api_key": SCRAPINGBEE_KEY,
                "url": url,
                "render_js": "false",
                "block_ads": "true",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        raise RuntimeError(f"Both direct fetch and ScrapingBee failed: {e}")


def _extract_apollo_products(html: str) -> List[Dict]:
    """Extract products from TPT's apolloState embedded in the HTML."""
    # Find the apolloState JSON in a <script> tag
    m = re.search(r'"apolloState"\s*:\s*(\{)', html)
    if not m:
        return []

    # Extract the full apolloState object by counting braces
    start = m.start(1)
    depth = 0
    end = start
    for i in range(start, min(start + 5_000_000, len(html))):
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end <= start:
        return []

    try:
        apollo = json.loads(html[start:end])
    except Exception as e:
        print(f"[scraper] apolloState parse error: {e}")
        return []

    # Find the searchResources key in ROOT_QUERY
    root = apollo.get("ROOT_QUERY", {})
    search_key = None
    for key in root:
        if key.startswith("searchResources("):
            search_key = key
            break

    if not search_key:
        print("[scraper] No searchResources key found in apolloState ROOT_QUERY")
        return []

    search_result = root[search_key]
    resource_refs = search_result.get("resources", [])
    if not resource_refs:
        # Sometimes nested under edges or items
        resource_refs = search_result.get("edges", []) or search_result.get("items", [])

    products = []
    for ref_obj in resource_refs:
        ref_key = ref_obj.get("__ref") if isinstance(ref_obj, dict) else None
        if not ref_key:
            continue
        resource = apollo.get(ref_key, {})
        if not resource:
            continue

        title = resource.get("title") or resource.get("name") or ""
        if not title:
            continue

        # Price — inline in pricing object (not a ref)
        price = 0.0
        original_price = None
        pricing = resource.get("pricing", {})
        if isinstance(pricing, dict):
            ntl = pricing.get("nonTransferableLicenses", {})
            if isinstance(ntl, dict):
                price = float(ntl.get("price", 0) or 0)
                raw_orig = ntl.get("originalPrice") or ntl.get("listPrice") or ntl.get("wasPrice")
                if raw_orig is not None:
                    op = float(raw_orig)
                    if op > price:
                        original_price = op

        # Rating — directly on resource
        rating = float(resource.get("overallQualityScore", 0) or 0)
        review_count = int(resource.get("totalEvaluations", 0) or 0)

        # Thumbnail — assets.thumbnails[0].largeUrl
        thumb = ""
        assets = resource.get("assets", {})
        if isinstance(assets, dict):
            thumbs = assets.get("thumbnails", [])
            if isinstance(thumbs, list) and thumbs:
                first = thumbs[0]
                if isinstance(first, dict):
                    thumb = first.get("largeUrl") or first.get("originalUrl") or ""

        # Author/Store — author.__ref → ResourceAuthor:xxx
        shop_name = ""
        shop_slug = ""
        author_ref = resource.get("author", {})
        if isinstance(author_ref, dict):
            author_key = author_ref.get("__ref")
            if author_key:
                author_obj = apollo.get(author_key, {})
                shop_name = author_obj.get("name", "")
                shop_slug = author_obj.get("slug", "")

        # URL
        slug = resource.get("canonicalSlug") or resource.get("slug") or ""
        rid = resource.get("id") or ref_key.split(":")[-1]
        if slug:
            url = f"https://www.teacherspayteachers.com/Product/{slug}"
        else:
            url = f"https://www.teacherspayteachers.com/Product/{rid}"

        products.append({
            "title": str(title)[:200],
            "url": url,
            "price": price,
            "original_price": original_price,
            "rating": rating,
            "reviews_total": review_count,
            "thumbnail": thumb,
            "shop_name": shop_name,
            "shop_url": f"https://www.teacherspayteachers.com/Store/{shop_slug}" if shop_slug else "",
            "has_bestseller": bool(resource.get("isBestSeller") or resource.get("bestSeller")),
            "has_image": bool(thumb),
        })

    print(f"[scraper] Apollo: found {len(products)} products from {len(resource_refs)} refs")
    return products


def _fetch_algolia(keyword: str, count: int = 30) -> List[Dict]:
    """Call TPT's Algolia search API directly — no JS rendering needed."""
    endpoint = f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    resp = requests.post(
        endpoint,
        headers={
            "x-algolia-application-id": ALGOLIA_APP_ID,
            "x-algolia-api-key": ALGOLIA_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "query": keyword,
            "hitsPerPage": count,
            "attributesToRetrieve": [
                "name", "price", "rating", "ratingCount", "id",
                "sellerName", "storeUrlName", "thumbnailUrl",
                "isBestSeller", "previewImages", "gradeMin", "gradeMax",
                "subjectList", "resourceTypeList",
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    products = []
    for r in hits:
        name = r.get("name", "")
        if not name:
            continue
        rid = r.get("id") or r.get("objectID") or ""
        url = f"https://www.teacherspayteachers.com/Product/{rid}" if rid else ""
        price_raw = r.get("price", 0)
        price = float(price_raw) / 100 if isinstance(price_raw, int) and price_raw > 100 else float(price_raw or 0)
        thumb = r.get("thumbnailUrl") or ""
        if not thumb and r.get("previewImages"):
            thumb = r["previewImages"][0].get("url", "") if isinstance(r["previewImages"], list) else ""
        products.append({
            "title": str(name)[:200],
            "url": url,
            "price": price,
            "rating": float(r.get("rating") or 0),
            "reviews_total": int(r.get("ratingCount") or 0),
            "thumbnail": thumb,
            "shop_name": r.get("sellerName") or "",
            "shop_url": f"https://www.teacherspayteachers.com/Store/{r.get('storeUrlName', '')}",
            "has_bestseller": bool(r.get("isBestSeller")),
            "has_image": bool(thumb),
            "grade_level": f"{r.get('gradeMin', '')}-{r.get('gradeMax', '')}".strip("-"),
            "category": ", ".join(r.get("subjectList", [])[:2]),
        })
    return products


def scrape_keyword_sync(keyword: str, count: int = 30) -> List[Dict]:
    """Scrape TPT search results using apolloState embedded in the HTML."""
    try:
        html = _fetch_tpt_search(keyword)
        products = _extract_apollo_products(html)
        if products:
            print(f"[scraper] ✅ {len(products)} real products via TPT apolloState for '{keyword}'")
            return _finalize(products[:count], keyword)
        print(f"[scraper] ⚠️ apolloState extraction returned 0 products for '{keyword}'")
    except Exception as e:
        print(f"[scraper] ⚠️ TPT fetch failed for '{keyword}': {e}")

    print(f"[scraper] ⚠️ Using mock data for '{keyword}'")
    return generate_mock_products(keyword, count)

def scrape_store_sync(store_name: str, count: int = 20) -> List[Dict]:
    """Scrape TPT store page."""
    url = f"https://www.teacherspayteachers.com/Store/{store_name}?order=Most+Reviewed"
    try:
        html = _fetch_html(url)
        products = _parse_search_page(html, store_name)
        for p in products:
            p["shop_name"] = store_name.replace("-", " ").title()
            p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{store_name}"
        if products:
            return products
    except Exception as e:
        print(f"[scraper] Store scrape failed for '{store_name}': {e}")
    mock = generate_mock_products(store_name, count)
    for p in mock:
        p["shop_name"] = store_name.replace("-", " ").title()
        p["shop_url"] = f"https://www.teacherspayteachers.com/Store/{store_name}"
    return mock

def scrape_product_page(product_url: str) -> dict:
    """Fetch a product page and extract extra fields from apolloState."""
    default = {
        "favorites": 0,
        "original_price": None,
        "date_published": "",
        "days_since_update": 90,
        "description_length": 0,
        "has_common_core": False,
        "preview_count": 0,
    }
    try:
        # Reuse _fetch_tpt_category logic but for a direct URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        html = None
        try:
            resp = requests.get(product_url, headers=headers, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                html = resp.text
        except Exception as e:
            print(f"[scraper] product page direct fetch failed: {e}")

        if not html and SCRAPINGBEE_KEY:
            resp = requests.get(
                SCRAPINGBEE_URL,
                params={"api_key": SCRAPINGBEE_KEY, "url": product_url, "render_js": "false", "block_ads": "true"},
                timeout=60,
            )
            resp.raise_for_status()
            html = resp.text

        if not html:
            print(f"[scraper] could not fetch product page {product_url}")
            return default

        # Try apolloState first
        m = re.search(r'"apolloState"\s*:\s*(\{)', html)
        if m:
            start = m.start(1)
            depth = 0
            end = start
            for i in range(start, min(start + 3_000_000, len(html))):
                c = html[i]
                if c == '{': depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                apollo = json.loads(html[start:end])
                # Find the resource object — look for Resource: keys
                resource = {}
                for key, val in apollo.items():
                    if key.startswith("Resource:") and isinstance(val, dict) and val.get("title"):
                        resource = val
                        break
                if not resource:
                    # Try ROOT_QUERY keys for resource(
                    root = apollo.get("ROOT_QUERY", {})
                    for key in root:
                        if key.startswith("resource(") or key.startswith("product("):
                            ref = root[key]
                            if isinstance(ref, dict) and ref.get("__ref"):
                                resource = apollo.get(ref["__ref"], {})
                            break

                result = dict(default)
                # Log resource keys for debugging (first time only)
                if resource:
                    print(f"[scraper] resource keys: {list(resource.keys())[:30]}")
                # favorites
                result["favorites"] = int(
                    resource.get("wishlistsCount") or resource.get("favoritesCount") or
                    resource.get("totalWishlists") or resource.get("savedCount") or
                    resource.get("totalSaves") or resource.get("listingFavorites") or 0
                )
                # original_price (promo detection)
                pricing = resource.get("pricing", {})
                if isinstance(pricing, dict):
                    ntl = pricing.get("nonTransferableLicenses", {})
                    if isinstance(ntl, dict):
                        current_price = float(ntl.get("price", 0) or 0)
                        raw_orig = ntl.get("originalPrice") or ntl.get("listPrice") or ntl.get("wasPrice")
                        if raw_orig is not None:
                            op = float(raw_orig)
                            result["original_price"] = op if op > current_price else None
                        if current_price > 0:
                            result["price"] = current_price
                # date_published
                date_str = (resource.get("datePosted") or resource.get("dateCreated") or
                            resource.get("publishedAt") or resource.get("createdAt") or
                            resource.get("listingDate") or resource.get("publishDate") or
                            resource.get("dateAdded") or resource.get("uploadedAt") or "")
                result["date_published"] = str(date_str)[:10] if date_str else ""
                # days_since_update
                last_activity = resource.get("dateLastActivity") or resource.get("dateModified") or resource.get("lastUpdated")
                if last_activity:
                    try:
                        from datetime import date
                        la_str = str(last_activity)[:10]
                        la_date = datetime.strptime(la_str, "%Y-%m-%d").date()
                        result["days_since_update"] = (date.today() - la_date).days
                    except Exception:
                        pass
                # description_length
                desc = (resource.get("description") or resource.get("body") or
                        resource.get("descriptionHtml") or resource.get("listingDescription") or
                        resource.get("fullDescription") or resource.get("content") or "")
                if isinstance(desc, dict):
                    desc = desc.get("text") or desc.get("html") or desc.get("value") or ""
                result["description_length"] = len(str(desc).split()) if desc else 0
                # has_common_core
                standards = resource.get("standardTags") or resource.get("standards") or resource.get("commonCore") or []
                if isinstance(standards, list):
                    result["has_common_core"] = any("common core" in str(s).lower() or "ccss" in str(s).lower() for s in standards)
                elif isinstance(standards, str):
                    result["has_common_core"] = "common core" in standards.lower() or "ccss" in standards.lower()
                # preview_count
                assets = resource.get("assets", {}) if isinstance(resource.get("assets"), dict) else {}
                previews = assets.get("previews") or assets.get("thumbnails") or resource.get("previewImages") or []
                result["preview_count"] = len(previews) if isinstance(previews, list) else 0

                print(f"[scraper] product page: favorites={result['favorites']}, desc_len={result['description_length']}, previews={result['preview_count']}")
                return result
            except Exception as e:
                print(f"[scraper] product page apolloState parse error: {e}")

        # Fallback: parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        result = dict(default)
        text = soup.get_text()
        # Try to find wishlist/favorites count
        m_fav = re.search(r'(\d[\d,]*)\s*(?:wish|favorit|saves)', text, re.I)
        if m_fav:
            result["favorites"] = int(m_fav.group(1).replace(",", ""))
        # Description length from meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["description_length"] = len(meta_desc["content"].split())
        print(f"[scraper] product page HTML fallback: {result}")
        return result
    except Exception as e:
        print(f"[scraper] scrape_product_page error: {e}")
        return default


def scrape_store_page(store_slug: str) -> dict:
    """Fetch a store page and extract store metrics from apolloState."""
    default = {
        "slug": store_slug,
        "name": store_slug.replace("-", " ").title(),
        "followers": 0,
        "nb_products": 0,
        "store_age_months": 0,
        "store_rating": 0.0,
        "store_reviews": 0,
        "nb_bestsellers": 0,
        "days_since_last_product": 30,
    }
    store_url = f"https://www.teacherspayteachers.com/Store/{store_slug}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        html = None
        try:
            resp = requests.get(store_url, headers=headers, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                html = resp.text
        except Exception as e:
            print(f"[scraper] store page direct fetch failed: {e}")

        if not html and SCRAPINGBEE_KEY:
            resp = requests.get(
                SCRAPINGBEE_URL,
                params={"api_key": SCRAPINGBEE_KEY, "url": store_url, "render_js": "false", "block_ads": "true"},
                timeout=60,
            )
            resp.raise_for_status()
            html = resp.text

        if not html:
            print(f"[scraper] could not fetch store page {store_url}")
            return default

        # Try apolloState
        m = re.search(r'"apolloState"\s*:\s*(\{)', html)
        if m:
            start = m.start(1)
            depth = 0
            end = start
            for i in range(start, min(start + 3_000_000, len(html))):
                c = html[i]
                if c == '{': depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                apollo = json.loads(html[start:end])
                root = apollo.get("ROOT_QUERY", {})
                seller_obj = {}
                # Find seller/store object
                for key in root:
                    if key.startswith("seller(") or key.startswith("store("):
                        ref = root[key]
                        if isinstance(ref, dict) and ref.get("__ref"):
                            seller_obj = apollo.get(ref["__ref"], {})
                        elif isinstance(ref, dict):
                            seller_obj = ref
                        break
                # Also check ResourceAuthor keys
                if not seller_obj:
                    for key, val in apollo.items():
                        if key.startswith("ResourceAuthor:") and isinstance(val, dict):
                            slug_val = val.get("slug", "")
                            if slug_val == store_slug or not slug_val:
                                seller_obj = val
                                break

                result = dict(default)
                result["followers"] = int(seller_obj.get("followerCount") or seller_obj.get("followers") or 0)
                result["nb_products"] = int(seller_obj.get("resourceCount") or seller_obj.get("productCount") or seller_obj.get("totalResources") or 0)
                result["store_rating"] = float(seller_obj.get("averageRating") or seller_obj.get("overallRating") or 0)
                result["store_reviews"] = int(seller_obj.get("totalEvaluations") or seller_obj.get("reviewCount") or 0)
                result["nb_bestsellers"] = int(seller_obj.get("bestsellerCount") or seller_obj.get("totalBestsellers") or 0)
                result["name"] = seller_obj.get("name") or result["name"]

                # Store age in months
                joined = seller_obj.get("dateJoined") or seller_obj.get("createdAt")
                if joined:
                    try:
                        j_str = str(joined)[:10]
                        j_date = datetime.strptime(j_str, "%Y-%m-%d")
                        now = datetime.now()
                        result["store_age_months"] = max(1, (now.year - j_date.year) * 12 + (now.month - j_date.month))
                    except Exception:
                        pass

                # Days since last product
                last_prod = seller_obj.get("lastResourceDate") or seller_obj.get("mostRecentProductDate")
                if last_prod:
                    try:
                        from datetime import date
                        lp_str = str(last_prod)[:10]
                        lp_date = datetime.strptime(lp_str, "%Y-%m-%d").date()
                        result["days_since_last_product"] = (date.today() - lp_date).days
                    except Exception:
                        pass

                print(f"[scraper] store page: slug={store_slug}, followers={result['followers']}, products={result['nb_products']}")
                return result
            except Exception as e:
                print(f"[scraper] store page apolloState parse error: {e}")

        # Fallback: parse HTML
        soup = BeautifulSoup(html, "html.parser")
        result = dict(default)
        text = soup.get_text()
        m_fol = re.search(r'(\d[\d,]*)\s*followers', text, re.I)
        if m_fol:
            result["followers"] = int(m_fol.group(1).replace(",", ""))
        m_prod = re.search(r'(\d[\d,]*)\s*(?:products|resources)', text, re.I)
        if m_prod:
            result["nb_products"] = int(m_prod.group(1).replace(",", ""))
        print(f"[scraper] store page HTML fallback: {result}")
        return result
    except Exception as e:
        print(f"[scraper] scrape_store_page error: {e}")
        return default


async def scrape_keyword(keyword: str, use_cache: bool = True) -> List[Dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, scrape_keyword_sync, keyword)

async def scrape_store(store_name: str) -> List[Dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, scrape_store_sync, store_name)


# ──────────────────────────────────────────────────────────────────────────────
# Mock data (fallback when ScrapingBee unavailable)
# ──────────────────────────────────────────────────────────────────────────────

SHOPS = [
    ("The Moffatt Girls", "the-moffatt-girls"),
    ("Deanna Jump", "deanna-jump"),
    ("Rachel Lynette", "rachel-lynette"),
    ("Lucky Little Learners", "lucky-little-learners"),
    ("Fun in Fifth Grade", "fun-in-fifth-grade"),
    ("The Curriculum Corner", "the-curriculum-corner"),
    ("Reagan Tunstall", "reagan-tunstall"),
    ("Jennifer Findley", "jennifer-findley"),
]
CAT_DISPLAY = ["Math","ELA","Science","Social Studies","SEL","Back to School","Teacher Tools","Classroom Decor"]
GRADES = ["K-2","3-5","6-8","9-12","PreK","All Grades"]
PRICES = [1.50,2.00,3.00,4.00,5.00,6.00,7.50,8.00,10.00,12.00,15.00,20.00]
TITLE_TPLS = [
    "{kw} Activities Bundle | Printable Worksheets",
    "{kw} Unit Study | Complete Curriculum Pack",
    "{kw} Task Cards | Boom Cards Digital",
    "Interactive {kw} Notebook | Foldables",
    "{kw} Assessment Pack | Tests & Quizzes",
    "{kw} Centers & Games | Differentiated",
    "{kw} Lesson Plans | Full Year Bundle",
    "{kw} Exit Tickets | Quick Checks",
]

def generate_mock_products(keyword: str, count: int = 20) -> List[Dict]:
    rng = random.Random(abs(hash(keyword)) % (2**31))
    kw = keyword.replace("-", " ").title()
    products = []
    for i in range(count):
        shop_name, shop_slug = rng.choice(SHOPS)
        rt = rng.randint(10, 3000)
        r30 = rng.randint(0, max(1, rt // 8))
        price = rng.choice(PRICES)
        rating = round(rng.uniform(3.5, 5.0), 1)
        bs = rng.random() < 0.2
        age_y = rng.uniform(0.5, 8)
        pub_year = datetime.now().year - int(age_y)
        pub_month = rng.randint(1, 12)
        pid = abs(hash(f"{keyword}-{i}")) % 9999999
        p = {
            "id": pid,
            "url": f"https://www.teacherspayteachers.com/Product/{kw.lower().replace(' ','-')}-{pid}",
            "title": rng.choice(TITLE_TPLS).format(kw=kw),
            "price": price,
            "rating": rating,
            "reviews_total": rt,
            "reviews_30j": r30,
            "favoris": rng.randint(5, rt * 2),
            "downloads": rng.randint(rt, rt * 15),
            "has_bestseller": bs,
            "has_image": True,
            "desc_words": rng.randint(100, 500),
            "category": rng.choice(CAT_DISPLAY),
            "grade_level": rng.choice(GRADES),
            "shop_name": shop_name,
            "shop_url": f"https://www.teacherspayteachers.com/Store/{shop_slug}",
            "date_published": f"{pub_year}-{pub_month:02d}-01",
            "thumbnail": f"https://picsum.photos/seed/{pid}/120/90",
            "keyword_searched": keyword,
            "scraped_at": datetime.now().isoformat(),
        }
        products.append(enrich_product(p, keyword))
    return products


# ──────────────────────────────────────────────────────────────────────────────
# Category-based scraping (TPT official URLs)
# ──────────────────────────────────────────────────────────────────────────────

# Shared state for tracking a running category scrape
_scrape_status: Dict[str, Any] = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current": "",
    "products_saved": 0,
    "errors": 0,
    "started_at": None,
    "finished_at": None,
}


def _fetch_tpt_category(tpt_url: str, sort_order: str, page: int) -> str:
    """Fetch a TPT category browse page via ScrapingBee."""
    full_url = f"https://www.teacherspayteachers.com{tpt_url}?order={requests.utils.quote(sort_order)}&page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(full_url, headers=headers, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and "apolloState" in resp.text:
            return resp.text
    except Exception:
        pass

    if not SCRAPINGBEE_KEY:
        raise RuntimeError("SCRAPINGBEE_API_KEY not set")

    resp = requests.get(
        SCRAPINGBEE_URL,
        params={
            "api_key": SCRAPINGBEE_KEY,
            "url": full_url,
            "render_js": "false",
            "block_ads": "true",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text


def scrape_category_url(tpt_url: str, category_name: str, category_id: str,
                        sort_order: str = "Most-Reviewed", page: int = 1) -> List[Dict]:
    """Scrape one page of a TPT category URL and return enriched products."""
    try:
        html = _fetch_tpt_category(tpt_url, sort_order, page)
        products = _extract_apollo_products(html)
        if not products:
            print(f"[scraper] ⚠️ No products from {tpt_url} sort={sort_order} page={page}")
            return []
        keyword = tpt_url.rstrip("/").split("/")[-1]
        enriched = _finalize(products, keyword)
        for p in enriched:
            p["category"] = category_name
            p["category_id"] = category_id
            p["category_url"] = tpt_url
            p["sort_order"] = sort_order
            p["page"] = page
        print(f"[scraper] ✅ {len(enriched)} products from {tpt_url} sort={sort_order} page={page}")
        return enriched
    except Exception as e:
        print(f"[scraper] ❌ {tpt_url} sort={sort_order} page={page}: {e}")
        return []


def scrape_all_categories(delay: float = 1.0, max_pages: int = 1) -> None:
    """
    Scrape all TPT leaf categories. Runs in a background thread.
    Imports categories_data to avoid circular imports at module load.
    """
    import time
    from categories_data import TPT_LEAF_CATEGORIES, SORT_ORDERS

    global _scrape_status

    pages_per_cat = max_pages
    total_requests = len(TPT_LEAF_CATEGORIES) * len(SORT_ORDERS) * pages_per_cat
    _scrape_status.update({
        "running": True,
        "progress": 0,
        "total": total_requests,
        "products_saved": 0,
        "errors": 0,
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
    })

    done = 0
    for cat in TPT_LEAF_CATEGORIES:
        if not _scrape_status["running"]:
            break
        for sort in SORT_ORDERS:
            for page in range(1, pages_per_cat + 1):
                if not _scrape_status["running"]:
                    break
                _scrape_status["current"] = f"{cat['name']} / {sort} / page {page}"
                products = scrape_category_url(cat["url"], cat["name"], cat["id"], sort, page)
                if not products:
                    _scrape_status["errors"] += 1
                done += 1
                _scrape_status["progress"] = done
                # Store products in DB synchronously via a new event loop call
                if products:
                    try:
                        from database import upsert_product_sync
                        saved = 0
                        for p in products:
                            try:
                                upsert_product_sync(p)
                                saved += 1
                            except Exception as e:
                                print(f"[scraper] DB save error ({type(e).__name__}): {e}")
                                break  # log once per batch, not 24 times
                        _scrape_status["products_saved"] += saved
                        if saved == 0 and products:
                            print(f"[scraper] WARNING: 0/{len(products)} saved in batch")
                    except Exception as e:
                        print(f"[scraper] DB batch error ({type(e).__name__}): {e}")
                time.sleep(delay)

    _scrape_status["running"] = False
    _scrape_status["finished_at"] = datetime.now().isoformat()
    print(f"[scraper] Category scrape complete: {_scrape_status['products_saved']} products saved, {_scrape_status['errors']} errors")


async def preload_demo_data():
    """Pre-load data for all categories on first startup."""
    try:
        from database import upsert_product, get_db_stats, set_cache
        stats = await get_db_stats()
        if stats["total_products"] > 50:
            return
        print("[scraper] Pre-loading data for all categories...")
        for cat in CATEGORIES[:6]:
            products = scrape_keyword_sync(cat, count=15)
            for p in products:
                try:
                    pid = await upsert_product(p)
                    p["id"] = pid
                except Exception:
                    pass
            await set_cache(cat)
            print(f"[scraper] ✅ {len(products)} products loaded for '{cat}'")
    except Exception as e:
        print(f"[scraper] preload error: {e}")
