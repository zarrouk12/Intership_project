"""Schemas M2 / M5 : diagnostic AS-IS et readiness."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AssessmentResponseBase(BaseModel):
    axis: str = Field(description="technique | metier")
    dimension_code: str
    dimension_label: str
    question: str | None = None
    score: float = Field(default=0.0, ge=0, le=5)
    weight: float = Field(default=1.0, gt=0)
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence: str | None = None
    owner: str | None = None
    is_critical: bool = False


class AssessmentResponseCreate(AssessmentResponseBase):
    pass


class AssessmentResponseUpdate(BaseModel):
    score: float | None = Field(default=None, ge=0, le=5)
    weight: float | None = Field(default=None, gt=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: str | None = None
    owner: str | None = None
    is_critical: bool | None = None


class AssessmentResponseOut(ORMModel, AssessmentResponseBase):
    id: int
    assessment_id: int


class AssessmentBase(BaseModel):
    name: str
    campaign: str | None = None
    site_id: int | None = None
    department_id: int | None = None
    status: str = "en_cours"
    started_on: date | None = None
    completed_on: date | None = None
    completion_rate: float = Field(default=0.0, ge=0, le=100)
    blocking_threshold: float = Field(default=2.5, ge=0, le=5)
    notes: str | None = None


class AssessmentCreate(AssessmentBase):
    responses: list[AssessmentResponseCreate] = []


class AssessmentUpdate(BaseModel):
    name: str | None = None
    campaign: str | None = None
    status: str | None = None
    completed_on: date | None = None
    completion_rate: float | None = Field(default=None, ge=0, le=100)
    blocking_threshold: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = None


class AssessmentOut(ORMModel, AssessmentBase):
    id: int
    organization_id: int


class AssessmentDetail(AssessmentOut):
    responses: list[AssessmentResponseOut] = []


class DimensionScoreOut(BaseModel):
    axis: str
    dimension_code: str
    dimension_label: str
    score: float
    weight: float
    confidence: float
    weighted_score: float
    max_weighted: float
    is_blocking: bool
    is_watch: bool = False
    is_critical: bool = False
    is_answered: bool = True
    evidence: str | None = None


class MaturityLevelOut(BaseModel):
    level: int
    label: str
    description: str


class ReadinessOut(BaseModel):
    global_score: float
    level: int
    level_label: str
    level_description: str
    technical_average: float
    business_average: float
    completion_rate: float
    answered_count: int = 0
    total_count: int = 0
    blocking_threshold: float
    dimensions: list[DimensionScoreOut]
    blocking_dimensions: list[DimensionScoreOut]
    watch_dimensions: list[DimensionScoreOut]
    pending_dimensions: list[DimensionScoreOut] = []
    maturity_scale: list[MaturityLevelOut]
