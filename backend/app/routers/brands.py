"""
ORYNT — Brands Router
POST /api/brands  — create a brand for the authenticated user's organization
GET  /api/brands  — list all brands for the authenticated user's organization
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.brand import Brand
from app.models.organization import Organization

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


class BrandCreate(BaseModel):
    name: str
    category: str


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
        raise HTTPException(
            status_code=404,
            detail="No organization found. Create an organization first.",
        )

    if body.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}",
        )

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
