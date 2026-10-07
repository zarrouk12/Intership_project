"""Schemas M11 : agregations pour les tableaux de bord."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.opportunity import MatrixPoint


class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    unit: str | None = None
    hint: str | None = None
    trend: str | None = None
    tone: str = "neutral"


class PhaseBucket(BaseModel):
    code: str
    label: str
    count: int
    share: float


class PortfolioRow(BaseModel):
    id: int
    code: str
    title: str
    department_name: str | None = None
    ai_type: str | None = None
    ai_type_label: str | None = None
    phase: str
    phase_label: str
    status: str
    priority_score: float
    priority_rank: int | None = None
    expected_benefit_eur: float
    risk_score: int


class DirectionDashboard(BaseModel):
    kpis: list[KpiCard]
    matrix: list[MatrixPoint]
    phases: list[PhaseBucket]
    top_priorities: list[PortfolioRow]
    readiness_global: float | None = None
    total_opportunities: int


class ValueDashboard(BaseModel):
    portfolio: dict
    kpis: list[dict]
    by_department: list[dict]
    roi_ranking: list[dict]
