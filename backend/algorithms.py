"""TPT Analyzer — Scoring Algorithms"""


def calculate_market_proof(reviews, rating, favorites):
    return (reviews * rating) + (favorites * 2)


def calculate_total_sales(reviews, favorites, is_bestseller, age_months):
    base = (reviews * 12) + (favorites * 3)
    bestseller_bonus = 1.3 if is_bestseller else 1.0
    if age_months < 6:
        age_correction = 1.4
    elif age_months <= 24:
        age_correction = 1.0
    else:
        age_correction = 0.85
    return base * bestseller_bonus * age_correction


def calculate_monthly_revenue(total_sales, age_months, price):
    if age_months == 0:
        age_months = 1
    monthly_sales = total_sales / age_months
    if 3 <= price <= 15:
        price_multiplier = 1.2
    elif price < 3:
        price_multiplier = 0.7
    elif price > 30:
        price_multiplier = 0.8
    else:
        price_multiplier = 1.0
    return monthly_sales * price * 0.55 * price_multiplier


def calculate_momentum(reviews_today, reviews_yesterday,
                       reviews_total, days_since_update):
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
    score = 0
    if rating > 4.5:
        score += 25
    elif rating > 4.0:
        score += 15
    if reviews > 100:
        score += 20
    elif reviews > 50:
        score += 10
    if description_length > 500:
        score += 15
    elif description_length > 200:
        score += 8
    if has_common_core:
        score += 15
    if preview_count >= 3:
        score += 15
    elif preview_count >= 1:
        score += 8
    if is_bestseller:
        score += 10
    return min(score, 100)


def calculate_opportunity_score(momentum_score, monthly_revenue, quality_score,
                                 age_months, max_momentum, max_revenue):
    if max_momentum > 0:
        momentum_norm = (momentum_score / max_momentum) * 100
    else:
        momentum_norm = 0
    if max_revenue > 0:
        revenue_norm = (monthly_revenue / max_revenue) * 100
    else:
        revenue_norm = 0
    if age_months < 6:
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
        quality_score * 0.20 +
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
    return round(product_opportunity * 0.70 + store_score * 0.30, 1)
