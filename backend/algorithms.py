"""TPT Analyzer — Scoring Algorithms"""


def calculate_market_proof(reviews, rating, favorites):
    return (reviews * rating) + (favorites * 2)


def calculate_total_sales(reviews):
    """reviews × 3 only (no favorites, no age correction)"""
    return reviews * 3


def calculate_monthly_revenue(total_sales, age_months, price):
    """
    Returns monthly revenue as float, or None if age_months is missing.
    Caps at $50,000/mo.
    """
    if age_months is None or age_months == 0:
        return None
    if 3 <= price <= 15:
        price_multiplier = 1.2
    elif price < 3:
        price_multiplier = 0.7
    elif price > 30:
        price_multiplier = 0.8
    else:
        price_multiplier = 1.0
    revenue_total = total_sales * price * 0.55 * price_multiplier
    monthly = revenue_total / age_months
    return min(monthly, 50000)


def calculate_momentum(reviews_today, reviews_yesterday,
                       reviews_total, days_since_update):
    """Returns no_data if no J-1 snapshot available."""
    if reviews_yesterday is None or reviews_yesterday == 0:
        return {
            "score": None,
            "status": "no_data",
            "emoji": "⏳",
            "message": "Disponible après 24h",
        }
    if reviews_total == 0:
        return {"score": 0, "status": "declining", "emoji": "📉"}
    reviews_gained = reviews_today - reviews_yesterday
    momentum = (reviews_gained / reviews_total) * 100
    if days_since_update < 30:
        momentum *= 1.2
    if momentum > 0.5:
        status = "exploding"
        emoji = "🔥"
    elif momentum > 0.2:
        status = "growing"
        emoji = "📈"
    elif momentum > 0.05:
        status = "stable"
        emoji = "➡️"
    else:
        status = "declining"
        emoji = "📉"
    return {
        "score": round(momentum, 3),
        "status": status,
        "emoji": emoji,
    }


def calculate_quality_score(rating, reviews, description_length,
                             has_common_core, preview_count, is_bestseller):
    """
    Returns {"score": X, "max_score": Y, "partial": bool}.
    Fields with None value are excluded from max_score.
    """
    score = 0
    max_score = 0

    # Rating (always available) — 25 pts
    max_score += 25
    if rating > 4.5:
        score += 25
    elif rating > 4.0:
        score += 15

    # Reviews (always available) — 20 pts
    max_score += 20
    if reviews > 100:
        score += 20
    elif reviews > 50:
        score += 10

    # Description length — 15 pts (optional)
    if description_length is not None:
        max_score += 15
        if description_length > 500:
            score += 15
        elif description_length > 200:
            score += 8

    # Common core — 15 pts (optional)
    if has_common_core is not None:
        max_score += 15
        if has_common_core:
            score += 15

    # Preview count — 15 pts (optional)
    if preview_count is not None:
        max_score += 15
        if preview_count >= 3:
            score += 15
        elif preview_count >= 1:
            score += 8

    # Bestseller — 10 pts (optional, default False)
    max_score += 10
    if is_bestseller:
        score += 10

    return {
        "score": score,
        "max_score": max_score,
        "partial": max_score < 100,
    }


def calculate_opportunity_score(momentum_score, monthly_revenue, quality_score,
                                 age_months, max_momentum, max_revenue):
    """Returns None if momentum or revenue data is missing."""
    if momentum_score is None or monthly_revenue is None:
        return None

    if max_momentum and max_momentum > 0:
        momentum_norm = (momentum_score / max_momentum) * 100
    else:
        momentum_norm = 0
    if max_revenue and max_revenue > 0:
        revenue_norm = (monthly_revenue / max_revenue) * 100
    else:
        revenue_norm = 0

    qs = quality_score if isinstance(quality_score, (int, float)) else quality_score.get("score", 0)
    qs_max = 100 if isinstance(quality_score, (int, float)) else quality_score.get("max_score", 100)
    qs_pct = (qs / qs_max * 100) if qs_max > 0 else 0

    if age_months is None:
        freshness = 0
    elif age_months < 6:
        freshness = 100
    elif age_months < 12:
        freshness = 75
    elif age_months < 24:
        freshness = 50
    else:
        freshness = 25

    score = (
        momentum_norm * 0.35 +
        revenue_norm * 0.30 +
        qs_pct * 0.20 +
        freshness * 0.15
    )
    return round(min(score, 100), 1)


# ─────────────────────────────── Store indicators ─────────────────────────────

def calculate_store_authority(store_reviews, store_rating,
                               followers, nb_bestsellers):
    return ((store_reviews * store_rating)
            + (followers * 3)
            + (nb_bestsellers * 50))


def calculate_store_productivity(nb_products, store_age_months,
                                  days_since_last_product):
    if store_age_months == 0:
        store_age_months = 1
    products_per_month = nb_products / store_age_months
    productivity = products_per_month * 10
    if days_since_last_product < 30:
        productivity += 20
    elif days_since_last_product < 90:
        productivity += 10
    return round(productivity, 1)


def calculate_store_consistency(main_category_pct, store_rating):
    if main_category_pct > 70:
        consistency = 100
    elif main_category_pct > 50:
        consistency = 70
    else:
        consistency = 40
    if store_rating > 4.5:
        consistency += 10
    elif store_rating > 4.0:
        consistency += 5
    return min(consistency, 100)


def calculate_store_score(authority, productivity, consistency,
                           store_rating, max_authority, max_productivity):
    if max_authority > 0:
        auth_norm = (authority / max_authority) * 100
    else:
        auth_norm = 0
    if max_productivity > 0:
        prod_norm = (productivity / max_productivity) * 100
    else:
        prod_norm = 0
    score = (
        auth_norm * 0.40 +
        prod_norm * 0.30 +
        consistency * 0.20 +
        (store_rating * 25) * 0.10
    )
    if score > 80:
        badge = "👑 Dominant"
    elif score > 60:
        badge = "✅ Solide"
    elif score > 40:
        badge = "⚠️ Moyen"
    else:
        badge = "🌱 Débutant"
    return {
        "score": round(min(score, 100), 1),
        "badge": badge,
    }


def calculate_final_opportunity(product_opportunity, store_score):
    if product_opportunity is None:
        return None
    return round(product_opportunity * 0.70 + store_score * 0.30, 1)


def _store_is_complete(store: dict) -> bool:
    """Store data considered complete if it has at least reviews and rating."""
    return bool(store.get("store_reviews") and store.get("store_rating"))


def enrich_product_full(product: dict, store: dict, yesterday_reviews,
                         all_products: list) -> dict:
    """
    Calculates all indicators for a product.
    all_products = list of all products in the batch (for normalizing max_momentum, max_revenue).
    Returns the product dict with 'indicators' and 'store_indicators' keys added.
    """
    # Extract product fields
    reviews_total = int(product.get("reviews_total") or 0)
    rating = float(product.get("rating") or 0)
    favorites = int(product.get("favorites") or product.get("favoris") or 0)
    price = float(product.get("price") or 0)
    is_bestseller = bool(product.get("has_bestseller") or False)
    days_since_update = int(product.get("days_since_update") or 90)

    # Optional fields — keep None if absent
    raw_desc = product.get("description_length") or product.get("desc_words")
    description_length = int(raw_desc) if raw_desc is not None else None

    raw_cc = product.get("has_common_core")
    has_common_core = bool(raw_cc) if raw_cc is not None else None

    raw_prev = product.get("preview_count")
    preview_count = int(raw_prev) if raw_prev is not None else None

    # age_months: None if no real date_publication
    raw_age = product.get("age_months")
    age_months = int(raw_age) if raw_age is not None and raw_age != "" else None

    # Extract store fields
    store_complete = _store_is_complete(store)
    store_reviews = int(store.get("store_reviews") or 0)
    store_rating = float(store.get("store_rating") or 0)
    followers = int(store.get("followers") or 0)
    nb_bestsellers = int(store.get("nb_bestsellers") or 0)
    nb_products = int(store.get("nb_products") or 0)
    store_age_months = int(store.get("store_age_months") or 1) or 1
    days_since_last_product = int(store.get("days_since_last_product") or 30)

    # Compute product indicators
    market_proof = calculate_market_proof(reviews_total, rating, favorites)
    total_sales = calculate_total_sales(reviews_total)
    monthly_revenue = calculate_monthly_revenue(total_sales, age_months, price)
    momentum = calculate_momentum(reviews_total, yesterday_reviews, reviews_total, days_since_update)
    quality = calculate_quality_score(rating, reviews_total, description_length,
                                      has_common_core, preview_count, is_bestseller)

    # Normalize across all products for opportunity score
    all_momentums = []
    all_revenues = []
    for p in all_products:
        rt = int(p.get("reviews_total") or 0)
        dsu = int(p.get("days_since_update") or 90)
        m = calculate_momentum(rt, None, rt, dsu)  # no J-1 for batch, use None
        if m["score"] is not None:
            all_momentums.append(m["score"])
        raw_a = p.get("age_months")
        p_age = int(raw_a) if raw_a is not None and raw_a != "" else None
        ts = calculate_total_sales(rt)
        rev = calculate_monthly_revenue(ts, p_age, float(p.get("price") or 0))
        if rev is not None:
            all_revenues.append(rev)

    max_momentum = max(all_momentums) if all_momentums else 1
    max_revenue = max(all_revenues) if all_revenues else 1

    # Store indicators
    if store_complete:
        authority = calculate_store_authority(store_reviews, store_rating, followers, nb_bestsellers)
        productivity = calculate_store_productivity(nb_products, store_age_months, days_since_last_product)
        main_category_pct = 60
        consistency = calculate_store_consistency(main_category_pct, store_rating)
        max_authority = max(authority, 1)
        max_productivity = max(productivity, 1)
        store_result = calculate_store_score(authority, productivity, consistency, store_rating,
                                             max_authority, max_productivity)
        store_indicators = {
            "authority": round(authority, 1),
            "productivity": round(productivity, 1),
            "consistency": consistency,
            "score": store_result["score"],
            "badge": store_result["badge"],
        }
        store_score_val = store_result["score"]
    else:
        store_indicators = {
            "score": None,
            "badge": "⏳ Store non analysé",
        }
        store_score_val = 0

    opportunity = calculate_opportunity_score(
        momentum["score"], monthly_revenue, quality,
        age_months, max_momentum, max_revenue
    )
    final = calculate_final_opportunity(opportunity, store_score_val)

    indicators = {
        "market_proof": round(market_proof, 1),
        "total_sales": total_sales,
        "monthly_revenue": round(monthly_revenue, 2) if monthly_revenue is not None else None,
        "momentum_score": momentum["score"],
        "momentum_status": momentum["status"],
        "momentum_emoji": momentum["emoji"],
        "momentum_message": momentum.get("message"),
        "quality_score": quality["score"],
        "quality_max_score": quality["max_score"],
        "quality_partial": quality["partial"],
        "opportunity_score": opportunity,
        "final_opportunity_score": final,
    }

    product["indicators"] = indicators
    product["store_indicators"] = store_indicators
    product["store"] = store
    return product
