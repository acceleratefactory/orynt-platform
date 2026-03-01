"""
ORYNT — SQLAlchemy Declarative Base
All ORM models inherit from this Base.
Import pattern: from app.models.base import Base
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORYNT ORM models."""
    pass
