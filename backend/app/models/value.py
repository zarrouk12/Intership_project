"""M10 - Valeur : couts (TCO), benefices et mesures de realisation."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class Cost(Base, TimestampMixin):
    """Ligne de cout entrant dans le TCO d'un projet ou d'une opportunite."""

    __tablename__ = "cost"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="build")
    nature: Mapped[str] = mapped_column(String(20), default="capex")
    amount_eur: Mapped[float] = mapped_column(Float, default=0.0)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    year: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class Benefit(Base, TimestampMixin):
    """Gain attendu, qualifie hard (P&L) ou soft."""

    __tablename__ = "benefit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    kpi_id: Mapped[int | None] = mapped_column(ForeignKey("kpi.id", ondelete="SET NULL"))
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="productivite")
    nature: Mapped[str] = mapped_column(String(20), default="hard")
    annual_amount_eur: Mapped[float] = mapped_column(Float, default=0.0)
    realization_rate: Mapped[float] = mapped_column(Float, default=1.0)
    pnl_line: Mapped[str | None] = mapped_column(String(80))
    start_year: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class Measurement(Base, TimestampMixin):
    """Relevé périodique d'un KPI (suivi de la valeur réellement captée)."""

    __tablename__ = "measurement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpi_id: Mapped[int] = mapped_column(
        ForeignKey("kpi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"))
    measured_on: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_label: Mapped[str | None] = mapped_column(String(60))
    source: Mapped[str | None] = mapped_column(String(160))
    comment: Mapped[str | None] = mapped_column(Text)
