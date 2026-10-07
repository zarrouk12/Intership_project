"""M3/M4/M6/M7 - Opportunites, recommandation IA et dependances interservices."""
from __future__ import annotations

from typing import Any, List

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import Phase, TimestampMixin


class Opportunity(Base, TimestampMixin):
    """Une idee/besoin metier qualifie, score et priorise."""

    __tablename__ = "opportunity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    site_id: Mapped[int | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    process_id: Mapped[int | None] = mapped_column(ForeignKey("process.id", ondelete="SET NULL"))

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    # --- Contexte AS-IS (M3) ---
    as_is_context: Mapped[str | None] = mapped_column(Text)
    pain_points: Mapped[str | None] = mapped_column(Text)
    desired_outcome: Mapped[str | None] = mapped_column(Text)

    # --- Gouvernance ---
    sponsor: Mapped[str | None] = mapped_column(String(160))
    business_owner: Mapped[str | None] = mapped_column(String(160))
    technical_owner: Mapped[str | None] = mapped_column(String(160))

    # --- Cycle de vie ---
    phase: Mapped[str] = mapped_column(String(40), default=Phase.QUALIFICATION, index=True)
    status: Mapped[str] = mapped_column(String(40), default="brouillon", index=True)

    # --- Questionnaire (commun + specifique departement) ---
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # --- Criteres de qualification (M4) ---
    data_available: Mapped[bool] = mapped_column(Boolean, default=False)
    data_structured: Mapped[bool] = mapped_column(Boolean, default=False)
    data_quality: Mapped[float] = mapped_column(Float, default=0.0)       # 0 -> 5
    ground_truth_available: Mapped[bool] = mapped_column(Boolean, default=False)
    unstructured_text: Mapped[bool] = mapped_column(Boolean, default=False)
    image_or_video: Mapped[bool] = mapped_column(Boolean, default=False)
    content_generation: Mapped[bool] = mapped_column(Boolean, default=False)
    multi_step_autonomy: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_based: Mapped[bool] = mapped_column(Boolean, default=False)
    repetitive_task: Mapped[bool] = mapped_column(Boolean, default=False)
    reporting_need: Mapped[bool] = mapped_column(Boolean, default=False)
    process_unstable: Mapped[bool] = mapped_column(Boolean, default=False)
    regulated_gxp: Mapped[bool] = mapped_column(Boolean, default=False)
    human_in_the_loop: Mapped[bool] = mapped_column(Boolean, default=True)
    volume_per_month: Mapped[int | None] = mapped_column(Integer)

    # --- Composantes de score (0 -> 100) ---
    impact_business: Mapped[float] = mapped_column(Float, default=0.0)
    impact_financial: Mapped[float] = mapped_column(Float, default=0.0)
    feasibility: Mapped[float] = mapped_column(Float, default=0.0)
    alignment: Mapped[float] = mapped_column(Float, default=0.0)
    readiness: Mapped[float] = mapped_column(Float, default=0.0)
    synergies: Mapped[float] = mapped_column(Float, default=0.0)

    # --- Risque (M7) : probabilite 1-5 x impact 1-5 ---
    risk_probability: Mapped[int] = mapped_column(Integer, default=1)
    risk_impact: Mapped[int] = mapped_column(Integer, default=1)

    # --- Resultats de priorisation ---
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority_rank: Mapped[int | None] = mapped_column(Integer)
    wave: Mapped[int | None] = mapped_column(Integer)
    score_explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # --- Valeur attendue (alimente la matrice impact x faisabilite) ---
    expected_benefit_eur: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_eur: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation: Mapped["AIRecommendation | None"] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    project: Mapped["Project | None"] = relationship(  # noqa: F821
        back_populates="opportunity", uselist=False
    )


class AIRecommendation(Base, TimestampMixin):
    """M4 - Sortie du moteur de qualification : type de solution + justification explicable."""

    __tablename__ = "ai_recommendation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    ai_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    ai_type_label: Mapped[str] = mapped_column(String(80), nullable=False)
    solution_pattern: Mapped[str | None] = mapped_column(String(200))
    rationale: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0 -> 1
    # Regles declenchees : [{code, label, poids, satisfait}]
    fired_rules: Mapped[list[dict] | None] = mapped_column(JSON)
    # Alternatives ecartees : [{type, label, score, raison}]
    alternatives: Mapped[list[dict] | None] = mapped_column(JSON)
    guardrails: Mapped[list[str] | None] = mapped_column(JSON)

    opportunity: Mapped[Opportunity] = relationship(back_populates="recommendation")


class Dependency(Base, TimestampMixin):
    """M6 - Croisement interservices : lien entre deux opportunites ou vers un actif partage."""

    __tablename__ = "dependency"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # data / process / kpi / application
    asset_ref: Mapped[str | None] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=1.0)    # 0 -> 1
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
