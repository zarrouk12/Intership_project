"""M2/M5 - Diagnostic AS-IS et readiness."""
from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Assessment(Base, TimestampMixin):
    """Campagne de diagnostic sur un site / un perimetre."""

    __tablename__ = "assessment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[int | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="en_cours")
    started_on: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # Seuil sous lequel une dimension est declaree bloquante (echelle 0-5)
    blocking_threshold: Mapped[float] = mapped_column(Float, default=2.5)
    notes: Mapped[str | None] = mapped_column(Text)

    responses: Mapped[List["AssessmentResponse"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", lazy="selectin"
    )


class AssessmentResponse(Base, TimestampMixin):
    """Une reponse = une dimension de maturite notee 0-5, ponderee et assortie d'une confiance."""

    __tablename__ = "assessment_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    axis: Mapped[str] = mapped_column(String(40), nullable=False)  # technique | metier
    dimension_code: Mapped[str] = mapped_column(String(80), nullable=False)
    dimension_label: Mapped[str] = mapped_column(String(200), nullable=False)
    question: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)        # 0 -> 5
    weight: Mapped[float] = mapped_column(Float, default=1.0)       # poids relatif
    confidence: Mapped[float] = mapped_column(Float, default=1.0)   # 0 -> 1
    evidence: Mapped[str | None] = mapped_column(Text)              # preuve / source
    # Une dimension critique sous le seuil bloque le passage en production ;
    # une dimension non critique sous le seuil est un point de vigilance.
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(160))

    assessment: Mapped[Assessment] = relationship(back_populates="responses")
