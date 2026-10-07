"""Schemas M10 : couts, benefices, mesures et business case."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CostBase(BaseModel):
    label: str
    category: str = "build"
    nature: str = "capex"
    amount_eur: float = 0.0
    recurring: bool = False
    year: int | None = None
    notes: str | None = None
    project_id: int | None = None
    opportunity_id: int | None = None


class CostCreate(CostBase):
    pass


class CostOut(ORMModel, CostBase):
    id: int
    organization_id: int


class BenefitBase(BaseModel):
    label: str
    category: str = "productivite"
    nature: str = "hard"
    annual_amount_eur: float = 0.0
    realization_rate: float = Field(default=1.0, ge=0, le=1)
    pnl_line: str | None = None
    start_year: int | None = None
    notes: str | None = None
    kpi_id: int | None = None
    project_id: int | None = None
    opportunity_id: int | None = None


class BenefitCreate(BenefitBase):
    pass


class BenefitOut(ORMModel, BenefitBase):
    id: int
    organization_id: int


class MeasurementBase(BaseModel):
    kpi_id: int
    project_id: int | None = None
    measured_on: date
    value: float
    period_label: str | None = None
    source: str | None = None
    comment: str | None = None


class MeasurementCreate(MeasurementBase):
    pass


class MeasurementOut(ORMModel, MeasurementBase):
    id: int
    organization_id: int


class BusinessCaseOut(BaseModel):
    horizon_years: int
    tco_eur: float
    capex_eur: float
    opex_annual_eur: float
    annual_benefit_eur: float
    cumulated_benefit_eur: float
    net_value_eur: float
    roi_percent: float
    payback_months: float | None = None
    pnl_breakdown: dict[str, float]
    costs: list[CostOut] = []
    benefits: list[BenefitOut] = []


class PortfolioValueOut(BaseModel):
    projects: int
    tco_eur: float
    annual_benefit_eur: float
    cumulated_benefit_eur: float
    net_value_eur: float
    roi_percent: float
    average_payback_months: float | None = None
