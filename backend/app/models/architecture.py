"""M6 - Referentiel d'architecture : processus, applications, sources de donnees, KPI."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class Process(Base, TimestampMixin):
    __tablename__ = "process"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    maturity: Mapped[float] = mapped_column(Float, default=0.0)          # 0 -> 5
    volume_per_month: Mapped[int | None] = mapped_column(Integer)
    manual_effort_days: Mapped[float | None] = mapped_column(Float)
    is_gxp: Mapped[bool] = mapped_column(Boolean, default=False)          # criticite reglementaire


class Application(Base, TimestampMixin):
    __tablename__ = "application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(80))  # ERP, LIMS, MES, QMS, CRM, DMS...
    has_api: Mapped[bool] = mapped_column(Boolean, default=False)
    criticality: Mapped[str | None] = mapped_column(String(40))
    validated_gxp: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DataSource(Base, TimestampMixin):
    __tablename__ = "datasource"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[int | None] = mapped_column(ForeignKey("application.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(60))        # structuree, texte, image, serie temporelle
    format: Mapped[str | None] = mapped_column(String(60))
    history_months: Mapped[int | None] = mapped_column(Integer)
    volume: Mapped[str | None] = mapped_column(String(80))
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 -> 5
    has_ground_truth: Mapped[bool] = mapped_column(Boolean, default=False)
    personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[str | None] = mapped_column(String(160))


class KPI(Base, TimestampMixin):
    __tablename__ = "kpi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40))
    direction: Mapped[str] = mapped_column(String(20), default="down")  # up = plus haut mieux
    baseline_value: Mapped[float | None] = mapped_column(Float)
    target_value: Mapped[float | None] = mapped_column(Float)
    current_value: Mapped[float | None] = mapped_column(Float)
    baseline_label: Mapped[str | None] = mapped_column(String(120))
    target_label: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
