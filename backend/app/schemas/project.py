"""Schemas M8 / M9 : projets, phases, jalons, taches, risques, incidents."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MitigationBase(BaseModel):
    action: str
    owner: str | None = None
    due_date: date | None = None
    status: str = "planifie"
    residual_probability: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)


class MitigationCreate(MitigationBase):
    risk_id: int


class MitigationOut(ORMModel, MitigationBase):
    id: int
    risk_id: int


class RiskBase(BaseModel):
    title: str
    category: str | None = None
    probability: int = Field(default=1, ge=1, le=5)
    impact: int = Field(default=1, ge=1, le=5)
    status: str = "ouvert"
    owner: str | None = None
    description: str | None = None
    project_id: int | None = None
    opportunity_id: int | None = None


class RiskCreate(RiskBase):
    pass


class RiskUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    probability: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    status: str | None = None
    owner: str | None = None
    description: str | None = None


class RiskOut(ORMModel, RiskBase):
    id: int
    organization_id: int
    severity: str
    score: int
    mitigations: list[MitigationOut] = []


class MilestoneBase(BaseModel):
    name: str
    due_date: date | None = None
    achieved_on: date | None = None
    status: str = "a_faire"
    is_gate: bool = False
    stage_id: int | None = None


class MilestoneCreate(MilestoneBase):
    project_id: int


class MilestoneOut(ORMModel, MilestoneBase):
    id: int
    project_id: int


class StageBase(BaseModel):
    code: str
    name: str
    sequence: int = 0
    status: str = "a_faire"
    gate_passed: bool = False
    gate_criteria: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None


class StageCreate(StageBase):
    project_id: int


class StageOut(ORMModel, StageBase):
    id: int
    project_id: int


class TaskBase(BaseModel):
    title: str
    assignee: str | None = None
    status: str = "a_faire"
    due_date: date | None = None
    effort_days: float | None = None
    description: str | None = None
    stage_id: int | None = None


class TaskCreate(TaskBase):
    project_id: int


class TaskOut(ORMModel, TaskBase):
    id: int
    project_id: int


class IssueBase(BaseModel):
    title: str
    severity: str = "moyenne"
    status: str = "ouvert"
    owner: str | None = None
    opened_on: date | None = None
    closed_on: date | None = None
    description: str | None = None
    context: dict[str, Any] | None = None


class IssueCreate(IssueBase):
    project_id: int


class IssueOut(ORMModel, IssueBase):
    id: int
    project_id: int


class ProjectBase(BaseModel):
    name: str
    opportunity_id: int | None = None
    department_id: int | None = None
    phase: str = "cadrage"
    status: str = "actif"
    sponsor: str | None = None
    business_owner: str | None = None
    technical_owner: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    next_gate_date: date | None = None
    next_gate_label: str | None = None
    budget_eur: float = 0.0
    committed_eur: float = 0.0
    progress: float = Field(default=0.0, ge=0, le=100)
    summary: str | None = None


class ProjectCreate(ProjectBase):
    code: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    phase: str | None = None
    status: str | None = None
    sponsor: str | None = None
    business_owner: str | None = None
    technical_owner: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    next_gate_date: date | None = None
    next_gate_label: str | None = None
    budget_eur: float | None = None
    committed_eur: float | None = None
    progress: float | None = Field(default=None, ge=0, le=100)
    summary: str | None = None


class ProjectOut(ORMModel, ProjectBase):
    id: int
    organization_id: int
    code: str


class ProjectDetail(ProjectOut):
    stages: list[StageOut] = []
    risks: list[RiskOut] = []


class GateRequest(BaseModel):
    stage_code: str
    decision: str = Field(description="go | no_go | revision")
    comment: str | None = None
    committee: str | None = None
