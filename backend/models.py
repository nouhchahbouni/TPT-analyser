from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Product(BaseModel):
    id: Optional[int] = None
    url: str
    title: str
    price: float = 0.0
    rating: float = 0.0
    reviews_total: int = 0
    reviews_30j: int = 0
    favoris: int = 0
    downloads: int = 0
    has_bestseller: bool = False
    has_image: bool = True
    desc_words: int = 0
    category: str = ""
    grade_level: str = ""
    shop_name: str = ""
    shop_url: str = ""
    date_published: Optional[str] = None
    thumbnail: str = ""
    keyword_searched: str = ""
    scraped_at: Optional[str] = None

    # Computed fields (not stored)
    total_sales: Optional[float] = None
    monthly_sales: Optional[float] = None
    monthly_revenue: Optional[float] = None
    total_revenue: Optional[float] = None
    momentum: Optional[float] = None
    optim_score: Optional[int] = None
    momentum_label: Optional[str] = None
    age_mois: Optional[int] = None


class SavedProduct(BaseModel):
    id: Optional[int] = None
    product_id: int
    saved_at: Optional[str] = None
    notes: Optional[str] = ""


class SaveProductRequest(BaseModel):
    product_id: int
    url: str = ""
    title: str = ""
    notes: str = ""


class ScrapeStatus(BaseModel):
    status: str
    message: str
    products_found: int = 0


class DashboardStats(BaseModel):
    total_products: int
    trending_count: int
    top_revenue: float
    best_category: str
    total_stores: int
    avg_optim_score: float
