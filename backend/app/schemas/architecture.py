"""Schemas M6 : processus, applications, sources de donnees, KPI."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProcessBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    department_id: int | None = None
    maturity: float = Field(default=0.0, ge=0, le=5)
    volume_per_month: int | None = None
    manual_effort_days: float | None = None
    is_gxp: bool = False


class ProcessCreate(ProcessBase):
    pass


class ProcessOut(ORMModel, ProcessBase):
    id: int
    organization_id: int


class ApplicationBase(BaseModel):
    name: str
    vendor: str | None = None
    category: str | None = None
    has_api: bool = False
    criticality: str | None = None
    validated_gxp: bool = False
    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationOut(ORMModel, ApplicationBase):
    id: int
    organization_id: int


class DataSourceBase(BaseModel):
    name: str
    application_id: int | None = None
    kind: str | None = None
    format: str | None = None
    history_months: int | None = None
    volume: str | None = None
    quality_score: float = Field(default=0.0, ge=0, le=5)
    has_ground_truth: bool = False
    personal_data: bool = False
    owner: str | None = None


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceOut(ORMModel, DataSourceBase):
    id: int
    organization_id: int


class KPIBase(BaseModel):
    code: str
    name: str
    unit: str | None = None
    direction: str = "down"
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    baseline_label: str | None = None
    target_label: str | None = None
    description: str | None = None
    department_id: int | None = None
    opportunity_id: int | None = None


class KPICreate(KPIBase):
    pass


class KPIUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    direction: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    baseline_label: str | None = None
    target_label: str | None = None
    description: str | None = None


class KPIOut(ORMModel, KPIBase):
    id: int
    organization_id: int


class KPIProgressOut(BaseModel):
    id: int
    code: str
    name: str
    unit: str | None = None
    direction: str
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    baseline_label: str | None = None
    target_label: str | None = None
    progress_percent: float | None = None
    opportunity_id: int | None = None
