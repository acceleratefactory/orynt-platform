"""
ORYNT — Brands Router
POST   /api/brands                         — create a brand
GET    /api/brands                         — list all brands in org
PATCH  /api/brands/{brand_id}             — update brand (seller_type, payment_methods, onboarding_completed)
POST   /api/brands/{brand_id}/products    — manual product entry
POST   /api/brands/{brand_id}/products/csv — bulk CSV upload
GET    /api/brands/{brand_id}/products    — list products for a brand
"""

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.brand import Brand, VALID_SELLER_TYPES
from app.models.organization import Organization
from app.models.product import Product

router = APIRouter(prefix="/brands", tags=["Brands"])

VALID_CATEGORIES = [
    "Fashion",
    "Food & Beverage",
    "Beauty & Skincare",
    "Electronics",
    "Home & Living",
    "Health & Wellness",
    "Digital Products",
    "Other",
]

VALID_PAYMENT_METHODS = [
    "paystack",
    "flutterwave",
    "monnify",
    "opay",
    "bank_transfer",
    "cash",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_brand_for_user(brand_id: str, user: dict, db: Session) -> Brand:
    """Fetch a brand that belongs to the authenticated user's organization."""
    owner_email = user.get("email")
    org = db.query(Organization).filter_by(owner_email=owner_email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    brand = db.query(Brand).filter_by(id=brand_id, organization_id=org.id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    return brand


# ─── Schemas ─────────────────────────────────────────────────────────────────

class BrandCreate(BaseModel):
    name: str
    category: str


class BrandUpdate(BaseModel):
    seller_type: Optional[str] = None
    payment_methods: Optional[List[str]] = None
    onboarding_completed: Optional[bool] = None


class ProductCreate(BaseModel):
    name: str
    selling_price: float
    cost_price: Optional[float] = None
    current_stock: int = 0
    sku_code: Optional[str] = None
    category: Optional[str] = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_brand(
    body: BrandCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a brand linked to the authenticated user's organization."""
    owner_email = user.get("email")
    org = db.query(Organization).filter_by(owner_email=owner_email).first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization found. Create an organization first.")

    if body.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")

    brand = Brand(name=body.name, category=body.category, organization_id=org.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand.to_dict()


@router.get("")
def get_brands(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all brands for the authenticated user's organization."""
    owner_email = user.get("email")
    org = db.query(Organization).filter_by(owner_email=owner_email).first()
    if not org:
        return []
    brands = db.query(Brand).filter_by(organization_id=org.id).all()
    return [b.to_dict() for b in brands]


@router.patch("/{brand_id}")
def update_brand(
    brand_id: str,
    body: BrandUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a brand — used by the onboarding flow to store:
    - seller_type (website | social_whatsapp | physical | digital)
    - payment_methods (list of selected payment gateways)
    - onboarding_completed (true when all steps are done)
    """
    brand = _get_brand_for_user(brand_id, user, db)

    if body.seller_type is not None:
        if body.seller_type not in VALID_SELLER_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid seller_type. Must be one of: {', '.join(VALID_SELLER_TYPES)}")
        brand.seller_type = body.seller_type

    if body.payment_methods is not None:
        invalid = [m for m in body.payment_methods if m not in VALID_PAYMENT_METHODS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid payment methods: {invalid}")
        brand.payment_methods = ",".join(body.payment_methods)

    if body.onboarding_completed is not None:
        brand.onboarding_completed = body.onboarding_completed

    db.commit()
    db.refresh(brand)
    return brand.to_dict()


@router.post("/{brand_id}/products", status_code=201)
def create_product(
    brand_id: str,
    body: ProductCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manual product entry — creates a single product scoped to this brand.
    For 'digital' seller types, is_digital is auto-set to True.
    """
    brand = _get_brand_for_user(brand_id, user, db)
    is_digital = brand.seller_type == "digital"

    product = Product(
        brand_id=brand_id,
        source="manual",
        name=body.name.strip(),
        selling_price=body.selling_price,
        cost_price=body.cost_price,
        current_stock=body.current_stock,
        sku_code=body.sku_code,
        category=body.category,
        is_digital=is_digital,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product.to_dict()


@router.post("/{brand_id}/products/csv", status_code=201)
async def upload_products_csv(
    brand_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk CSV upload — expected columns:
    name, selling_price, cost_price (optional), current_stock (optional), sku_code (optional), category (optional)
    Deduplication: skips rows where (sku_code + source='csv') already exists for this brand.
    """
    brand = _get_brand_for_user(brand_id, user, db)
    is_digital = brand.seller_type == "digital"

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file.")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")  # Handle BOM from Excel csv exports
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding must be UTF-8.")

    reader = csv.DictReader(io.StringIO(decoded))
    required_cols = {"name", "selling_price"}
    if not required_cols.issubset(set(reader.fieldnames or [])):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain columns: {required_cols}. Found: {reader.fieldnames}"
        )

    created, skipped = 0, 0
    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            skipped += 1
            continue

        try:
            selling_price = float(row.get("selling_price", 0) or 0)
        except ValueError:
            skipped += 1
            continue

        sku_code = row.get("sku_code", "").strip() or None
        cost_price_raw = row.get("cost_price", "").strip()
        cost_price = float(cost_price_raw) if cost_price_raw else None
        stock_raw = row.get("current_stock", "0").strip()
        current_stock = int(stock_raw) if stock_raw.isdigit() else 0
        category = row.get("category", "").strip() or None

        # Deduplication: skip if sku_code already exists for this brand from csv source
        if sku_code:
            existing = db.query(Product).filter_by(
                brand_id=brand_id, sku_code=sku_code, source="csv"
            ).first()
            if existing:
                skipped += 1
                continue

        product = Product(
            brand_id=brand_id,
            source="csv",
            name=name,
            selling_price=selling_price,
            cost_price=cost_price,
            current_stock=current_stock,
            sku_code=sku_code,
            category=category,
            is_digital=is_digital,
        )
        db.add(product)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/{brand_id}/products")
def get_products(
    brand_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all products for a brand, scoped to the authenticated user's organization."""
    brand = _get_brand_for_user(brand_id, user, db)
    products = db.query(Product).filter_by(brand_id=brand_id, is_active=True).all()
    return [p.to_dict() for p in products]
