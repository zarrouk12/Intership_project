"""Schemas M3 / M4 / M6 / M7 : opportunites, qualification, priorisation, dependances."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RecommendationOut(ORMModel):
    id: int
    opportunity_id: int
    ai_type: str
    ai_type_label: str
    solution_pattern: str | None = None
    rationale: str | None = None
    confidence: float
    fired_rules: list[dict] | None = None
    alternatives: list[dict] | None = None
    guardrails: list[str] | None = None


class OpportunityBase(BaseModel):
    title: str
    summary: str | None = None
    department_id: int | None = None
    site_id: int | None = None
    process_id: int | None = None

    as_is_context: str | None = None
    pain_points: str | None = None
    desired_outcome: str | None = None

    sponsor: str | None = None
    business_owner: str | None = None
    technical_owner: str | None = None

    phase: str = "qualification"
    status: str = "brouillon"
    answers: dict[str, Any] = Field(default_factory=dict)

    data_available: bool = False
    data_structured: bool = False
    data_quality: float = Field(default=0.0, ge=0, le=5)
    ground_truth_available: bool = False
    unstructured_text: bool = False
    image_or_video: bool = False
    content_generation: bool = False
    multi_step_autonomy: bool = False
    rule_based: bool = False
    repetitive_task: bool = False
    reporting_need: bool = False
    process_unstable: bool = False
    regulated_gxp: bool = False
    human_in_the_loop: bool = True
    volume_per_month: int | None = None

    impact_business: float = Field(default=0.0, ge=0, le=100)
    impact_financial: float = Field(default=0.0, ge=0, le=100)
    feasibility: float = Field(default=0.0, ge=0, le=100)
    alignment: float = Field(default=0.0, ge=0, le=100)
    readiness: float = Field(default=0.0, ge=0, le=100)
    synergies: float = Field(default=0.0, ge=0, le=100)

    risk_probability: int = Field(default=1, ge=1, le=5)
    risk_impact: int = Field(default=1, ge=1, le=5)

    expected_benefit_eur: float = 0.0
    estimated_cost_eur: float = 0.0


class OpportunityCreate(OpportunityBase):
    code: str | None = None


class OpportunityUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    department_id: int | None = None
    site_id: int | None = None
    process_id: int | None = None
    as_is_context: str | None = None
    pain_points: str | None = None
    desired_outcome: str | None = None
    sponsor: str | None = None
    business_owner: str | None = None
    technical_owner: str | None = None
    phase: str | None = None
    status: str | None = None
    answers: dict[str, Any] | None = None

    data_available: bool | None = None
    data_structured: bool | None = None
    data_quality: float | None = Field(default=None, ge=0, le=5)
    ground_truth_available: bool | None = None
    unstructured_text: bool | None = None
    image_or_video: bool | None = None
    content_generation: bool | None = None
    multi_step_autonomy: bool | None = None
    rule_based: bool | None = None
    repetitive_task: bool | None = None
    reporting_need: bool | None = None
    process_unstable: bool | None = None
    regulated_gxp: bool | None = None
    human_in_the_loop: bool | None = None
    volume_per_month: int | None = None

    impact_business: float | None = Field(default=None, ge=0, le=100)
    impact_financial: float | None = Field(default=None, ge=0, le=100)
    feasibility: float | None = Field(default=None, ge=0, le=100)
    alignment: float | None = Field(default=None, ge=0, le=100)
    readiness: float | None = Field(default=None, ge=0, le=100)
    synergies: float | None = Field(default=None, ge=0, le=100)
    risk_probability: int | None = Field(default=None, ge=1, le=5)
    risk_impact: int | None = Field(default=None, ge=1, le=5)

    expected_benefit_eur: float | None = None
    estimated_cost_eur: float | None = None


class OpportunityOut(ORMModel, OpportunityBase):
    id: int
    organization_id: int
    code: str
    priority_score: float
    priority_rank: int | None = None
    wave: int | None = None
    score_explanation: dict[str, Any] | None = None
    recommendation: RecommendationOut | None = None
    department_name: str | None = None
    site_name: str | None = None


class ScoreContribution(BaseModel):
    criterion: str
    label: str
    value: float
    weight: float
    contribution: float


class ScoreExplanationOut(BaseModel):
    priority_score: float
    weighted_sum: float
    risk_score: int
    risk_penalty: float
    max_risk_penalty: float
    weights: dict[str, float]
    contributions: list[ScoreContribution]
    formula: str


class ScoringWeights(BaseModel):
    impact_business: float | None = Field(default=None, ge=0)
    impact_financial: float | None = Field(default=None, ge=0)
    feasibility: float | None = Field(default=None, ge=0)
    alignment: float | None = Field(default=None, ge=0)
    readiness: float | None = Field(default=None, ge=0)
    synergies: float | None = Field(default=None, ge=0)


class PrioritizeRequest(BaseModel):
    weights: ScoringWeights | None = None
    wave_size: int = Field(default=6, ge=1, le=50)
    # Recalcul du critere de synergie depuis le graphe de dependances (M6). Desactive par
    # defaut : il ecrase les valeurs evaluees en atelier, ce qui doit rester un acte explicite.
    apply_synergies: bool = False


class PrioritizedItem(BaseModel):
    id: int
    code: str
    title: str
    priority_score: float
    priority_rank: int
    wave: int
    department_name: str | None = None
    ai_type_label: str | None = None
    phase: str
    status: str


class PrioritizeResult(BaseModel):
    weights: dict[str, float]
    items: list[PrioritizedItem]


class DependencyBase(BaseModel):
    source_opportunity_id: int
    target_opportunity_id: int | None = None
    kind: str
    asset_ref: str | None = None
    label: str
    strength: float = Field(default=1.0, ge=0, le=1)
    is_blocking: bool = False
    notes: str | None = None


class DependencyCreate(DependencyBase):
    pass


class DependencyOut(ORMModel, DependencyBase):
    id: int
    organization_id: int


class DuplicatePair(BaseModel):
    source_id: int
    source_code: str
    source_title: str
    target_id: int
    target_code: str
    target_title: str
    similarity: float
    lexical_similarity: float
    asset_overlap: float
    context_overlap: float
    shared_terms: list[str]
    shared_assets: list[str]
    verdict: str


class MatrixPoint(BaseModel):
    id: int
    code: str
    title: str
    impact: float
    feasibility: float
    benefit: float
    ai_type: str | None = None
    ai_type_label: str | None = None
    quadrant: str
    priority_score: float
