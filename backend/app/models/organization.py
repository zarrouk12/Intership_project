"""M1 - Organisation : entreprise, sites, departements."""
from __future__ import annotations

from typing import List

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(120), default="Pharmaceutique")
    country: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

    sites: Mapped[List["Site"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    departments: Mapped[List["Department"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class Site(Base, TimestampMixin):
    __tablename__ = "site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(80))
    site_type: Mapped[str | None] = mapped_column(String(80))  # production / R&D / siege / distribution

    organization: Mapped[Organization] = relationship(back_populates="sites")
    departments: Mapped[List["Department"]] = relationship(back_populates="site")


class Department(Base, TimestampMixin):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[int | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    # Famille metier pour le questionnaire specifique (M3)
    family: Mapped[str | None] = mapped_column(String(80))
    head_name: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship(back_populates="departments")
    site: Mapped[Site | None] = relationship(back_populates="departments")
