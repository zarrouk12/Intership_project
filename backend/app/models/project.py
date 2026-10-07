"""M8/M9 - Fiche projet, cycle de vie, risques et incidents."""
from __future__ import annotations

from datetime import date
from typing import Any, List

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import Phase, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="SET NULL"), unique=True, index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    phase: Mapped[str] = mapped_column(String(40), default=Phase.FRAMING, index=True)
    status: Mapped[str] = mapped_column(String(40), default="actif", index=True)
    sponsor: Mapped[str | None] = mapped_column(String(160))
    business_owner: Mapped[str | None] = mapped_column(String(160))
    technical_owner: Mapped[str | None] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_gate_date: Mapped[date | None] = mapped_column(Date)
    next_gate_label: Mapped[str | None] = mapped_column(String(200))
    budget_eur: Mapped[float] = mapped_column(Float, default=0.0)
    committed_eur: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text)

    opportunity: Mapped["Opportunity | None"] = relationship(back_populates="project")
    stages: Mapped[List["Stage"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    risks: Mapped[List["Risk"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )


class Stage(Base, TimestampMixin):
    """Phase TOGAF instanciee sur un projet, avec sa gate de sortie."""

    __tablename__ = "stage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="a_faire")
    gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    gate_criteria: Mapped[list[str] | None] = mapped_column(JSON)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    project: Mapped[Project] = relationship(back_populates="stages")
    milestones: Mapped[List["Milestone"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class Milestone(Base, TimestampMixin):
    __tablename__ = "milestone"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("stage.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    achieved_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="a_faire")
    is_gate: Mapped[bool] = mapped_column(Boolean, default=False)

    stage: Mapped[Stage | None] = relationship(back_populates="milestones")


class Task(Base, TimestampMixin):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("stage.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), default="a_faire")
    due_date: Mapped[date | None] = mapped_column(Date)
    effort_days: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)


class Risk(Base, TimestampMixin):
    __tablename__ = "risk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    probability: Mapped[int] = mapped_column(Integer, default=1)
    impact: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[str] = mapped_column(String(40), default="faible")
    status: Mapped[str] = mapped_column(String(40), default="ouvert")
    owner: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project | None] = relationship(back_populates="risks")
    mitigations: Mapped[List["Mitigation"]] = relationship(
        back_populates="risk", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def score(self) -> int:
        return int(self.probability or 0) * int(self.impact or 0)


class Mitigation(Base, TimestampMixin):
    __tablename__ = "mitigation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_id: Mapped[int] = mapped_column(
        ForeignKey("risk.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(300), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(160))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="planifie")
    residual_probability: Mapped[int | None] = mapped_column(Integer)
    residual_impact: Mapped[int | None] = mapped_column(Integer)

    risk: Mapped[Risk] = relationship(back_populates="mitigations")


class Issue(Base, TimestampMixin):
    __tablename__ = "issue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="moyenne")
    status: Mapped[str] = mapped_column(String(40), default="ouvert")
    owner: Mapped[str | None] = mapped_column(String(160))
    opened_on: Mapped[date | None] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
