"""TPT Analyzer — Score Calculation Algorithms"""


def calc_age_mois(date_published: str) -> int:
    """Calculate product age in months from publication date string."""
    if not date_published:
        return 12  # default to 1 year
    from datetime import datetime
    try:
        # Try various date formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y"):
            try:
                pub = datetime.strptime(date_published, fmt)
                now = datetime.now()
                diff = (now.year - pub.year) * 12 + (now.month - pub.month)
                return max(diff, 1)
            except ValueError:
                continue
        return 12
    except Exception:
        return 12


def calc_total_sales(reviews_total: int, favoris: int, downloads: int,
                     has_bestseller: bool, age_mois: int) -> float:
    base = reviews_total * 12
    bonus_favoris = favoris * 3
    bonus_downloads = downloads * 0.8
    bonus_bestseller = 1.3 if has_bestseller else 1.0
    if age_mois < 6:
        correction_age = 1.4
    elif age_mois <= 24:
        correction_age = 1.0
    else:
        correction_age = 0.85
    return (base + bonus_favoris + bonus_downloads) * bonus_bestseller * correction_age


def calc_monthly_sales(total_sales: float, age_mois: int) -> float:
    return total_sales / max(age_mois, 1)


def calc_revenue(sales: float, price: float) -> float:
    return sales * price * 0.55


def calc_momentum(reviews_30j: int, reviews_total: int) -> float:
    if reviews_total == 0:
        return 0.0
    return (reviews_30j / reviews_total) * 100


def get_momentum_label(momentum: float) -> str:
    """Return emoji label for momentum score."""
    if momentum > 15:
        return "🔥"
    elif momentum >= 8:
        return "📈"
    elif momentum >= 3:
        return "➡️"
    else:
        return "📉"


def calc_optimization_score(title: str, keyword: str, rating: float, price: float,
                             has_bestseller: bool, has_image: bool, desc_words: int) -> int:
    score = 0
    if keyword and keyword.lower() in title.lower():
        score += 25
    if rating > 3.8:
        score += 20
    if 3 <= price <= 15:
        score += 20
    if has_bestseller:
        score += 15
    if has_image:
        score += 10
    if desc_words > 200:
        score += 10
    return score


def enrich_product(product: dict, keyword: str = "") -> dict:
    """Add all computed fields to a product dict."""
    age_mois = calc_age_mois(product.get("date_published", ""))
    reviews_total = product.get("reviews_total", 0)
    reviews_30j = product.get("reviews_30j", 0)
    favoris = product.get("favoris", 0)
    downloads = product.get("downloads", 0)
    has_bestseller = product.get("has_bestseller", False)
    has_image = product.get("has_image", True)
    desc_words = product.get("desc_words", 0)
    price = product.get("price", 0.0)
    rating = product.get("rating", 0.0)
    title = product.get("title", "")

    total_sales = calc_total_sales(reviews_total, favoris, downloads, has_bestseller, age_mois)
    monthly_sales = calc_monthly_sales(total_sales, age_mois)
    momentum = calc_momentum(reviews_30j, reviews_total)
    optim_score = calc_optimization_score(title, keyword, rating, price, has_bestseller, has_image, desc_words)

    product["age_mois"] = age_mois
    product["total_sales"] = round(total_sales, 1)
    product["monthly_sales"] = round(monthly_sales, 1)
    product["monthly_revenue"] = round(calc_revenue(monthly_sales, price), 2)
    product["total_revenue"] = round(calc_revenue(total_sales, price), 2)
    product["momentum"] = round(momentum, 2)
    product["momentum_label"] = get_momentum_label(momentum)
    product["optim_score"] = optim_score
    return product
