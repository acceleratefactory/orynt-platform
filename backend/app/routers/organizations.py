"""
ORYNT — Organizations Router
POST /api/organizations  — create an organization for the authenticated user
GET  /api/organizations/me — get the authenticated user's organization
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.organization import Organization

router = APIRouter(prefix="/organizations", tags=["Organizations"])


class OrganizationCreate(BaseModel):
    name: str
    owner_phone: str = ""


@router.post("", status_code=201)
def create_organization(
    body: OrganizationCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create an organization for the authenticated user.
    If one already exists, return the existing one without error.
    """
    owner_email = user.get("email")
    if not owner_email:
        raise HTTPException(status_code=400, detail="JWT does not contain an email claim.")

    existing = db.query(Organization).filter_by(owner_email=owner_email).first()
    if existing:
        return existing.to_dict()

    org = Organization(
        name=body.name,
        owner_email=owner_email,
        owner_phone=body.owner_phone or None,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org.to_dict()


@router.get("/me")
def get_my_organization(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the organization belonging to the authenticated user."""
    owner_email = user.get("email")
    org = db.query(Organization).filter_by(owner_email=owner_email).first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization found for this user.")
    return org.to_dict()
