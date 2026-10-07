"""M3 / M4 / M7 - Opportunites, moteur de qualification et priorisation."""
from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.models.rbac import User
from app.api.deps import (
    CurrentUser,
    DbSession,
    Scope,
    TenantId,
    get_or_404,
    get_scoped_or_404,
    require_permission,
)
from app.models.base import AIType, Phase
from app.models.opportunity import AIRecommendation, Dependency, Opportunity
from app.models.organization import Department, Site
from app.schemas.opportunity import (
    MatrixPoint,
    OpportunityCreate,
    OpportunityOut,
    OpportunityUpdate,
    PrioritizeRequest,
    PrioritizeResult,
    PrioritizedItem,
    RecommendationOut,
    ScoreExplanationOut,
)
from app.services import crossing, recommendation, scoring
from app.services.audit import log_action, log_update, snapshot
from app.services.questionnaire import questionnaire_for

router = APIRouter(prefix="/opportunities", tags=["M3/M4/M7 - Opportunites"])


# --------------------------------------------------------------------------- utilitaires
def _decorate(db, opportunities: Iterable[Opportunity]) -> list[Opportunity]:
    """Ajoute les libelles de departement et de site attendus par le frontend."""
    items = list(opportunities)
    dept_names = dict(db.execute(select(Department.id, Department.name)).all())
    site_names = dict(db.execute(select(Site.id, Site.name)).all())
    for o in items:
        o.department_name = dept_names.get(o.department_id)
        o.site_name = site_names.get(o.site_id)
    return items


def _next_code(db, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count(Opportunity.id)).where(Opportunity.organization_id == tenant_id)
    )
    return f"OPP-2026-{(count or 0) + 1:03d}"


def _apply_recommendation(db, tenant_id: int, opportunity: Opportunity) -> AIRecommendation:
    result = recommendation.qualify(opportunity)
    reco = opportunity.recommendation
    if reco is None:
        reco = AIRecommendation(organization_id=tenant_id, opportunity_id=opportunity.id)
        db.add(reco)
    reco.ai_type = result["ai_type"]
    reco.ai_type_label = result["ai_type_label"]
    reco.solution_pattern = result["solution_pattern"]
    reco.rationale = result["rationale"]
    reco.confidence = result["confidence"]
    reco.fired_rules = result["fired_rules"]
    reco.alternatives = result["alternatives"]
    reco.guardrails = result["guardrails"]
    db.flush()
    return reco


def _rescore(opportunity: Opportunity, weights: dict | None = None) -> dict:
    breakdown = scoring.score_opportunity(opportunity, weights)
    opportunity.priority_score = breakdown.priority_score
    opportunity.score_explanation = breakdown.as_dict()
    return opportunity.score_explanation


# ------------------------------------------------------------------------------ lecture
@router.get("", response_model=list[OpportunityOut], summary="Lister et filtrer le portefeuille")
def list_opportunities(
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.read")),
    department_id: int | None = None,
    site_id: int | None = None,
    ai_type: str | None = Query(default=None, description="ia_classique, generative, agentique..."),
    phase: str | None = None,
    status: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    search: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Opportunity]:
    stmt = select(Opportunity).where(Opportunity.organization_id == tenant_id)
    if department_id:
        stmt = stmt.where(Opportunity.department_id == department_id)
    if site_id:
        stmt = stmt.where(Opportunity.site_id == site_id)
    if phase:
        stmt = stmt.where(Opportunity.phase == phase)
    if status:
        stmt = stmt.where(Opportunity.status == status)
    if min_score is not None:
        stmt = stmt.where(Opportunity.priority_score >= min_score)
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(Opportunity.title).like(pattern) | func.lower(Opportunity.code).like(pattern)
        )
    if ai_type:
        stmt = stmt.join(AIRecommendation).where(AIRecommendation.ai_type == ai_type)

    # Perimetre departemental : la liste ne montre que les departements de rattachement.
    stmt = scope.filter_by_department(stmt, Opportunity.department_id)
    stmt = stmt.order_by(Opportunity.priority_score.desc()).limit(limit).offset(offset)
    return _decorate(db, db.scalars(stmt).unique())


@router.get("/reference", summary="Referentiels : types de solution, phases, statuts")
def reference(current_user: User = Depends(require_permission("opportunity.read"))) -> dict:
    return {
        "ai_types": [{"code": c, "label": AIType.LABELS[c]} for c in AIType.ALL],
        "phases": [{"code": c, "label": Phase.LABELS[c]} for c in Phase.ALL],
        "statuses": [
            {"code": "brouillon", "label": "Brouillon"},
            {"code": "evalue", "label": "Évalué"},
            {"code": "business_case", "label": "Business case"},
            {"code": "approuve", "label": "Approuvé"},
            {"code": "en_poc", "label": "En POC"},
            {"code": "en_attente", "label": "En attente"},
            {"code": "rejete", "label": "Rejeté"},
        ],
        "scoring_weights": scoring.DEFAULT_WEIGHTS,
    }


@router.get("/questionnaire", summary="M3 - Questionnaire commun et specifique au departement")
def questionnaire(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("opportunity.read")),
    department_id: int | None = None,
) -> dict:
    family = None
    if department_id:
        dept = db.get(Department, department_id)
        if dept and dept.organization_id == tenant_id:
            family = dept.family
    return questionnaire_for(family)


@router.get("/matrix", response_model=list[MatrixPoint], summary="Matrice Impact x Faisabilite")
def matrix(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("portfolio.read")),
) -> list[dict]:
    opportunities = db.scalars(
        select(Opportunity).where(Opportunity.organization_id == tenant_id)
    ).unique()
    return scoring.portfolio_matrix(opportunities)


@router.get("/{opportunity_id}", response_model=OpportunityOut, summary="Detail d'une opportunite")
def read_opportunity(
    opportunity_id: int,
    db: DbSession,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.read")),
) -> Opportunity:
    opportunity = get_scoped_or_404(db, Opportunity, opportunity_id, scope, "Opportunite")
    return _decorate(db, [opportunity])[0]


# ------------------------------------------------------------------------------ ecriture
@router.post("", response_model=OpportunityOut, status_code=201, summary="Creer une opportunite")
def create_opportunity(
    payload: OpportunityCreate,
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.create")),
) -> Opportunity:
    # Un utilisateur au perimetre departemental ne depose que dans ses departements.
    scope.assert_can_write_department(payload.department_id, "une opportunite de ce departement")
    data = payload.model_dump(exclude={"code"})
    opportunity = Opportunity(
        organization_id=tenant_id,
        code=payload.code or _next_code(db, tenant_id),
        **data,
    )
    db.add(opportunity)
    db.flush()

    _apply_recommendation(db, tenant_id, opportunity)
    _rescore(opportunity)
    db.flush()

    log_action(
        db,
        action="create",
        entity_type="opportunity",
        entity_id=opportunity.id,
        entity_label=opportunity.title,
        organization_id=tenant_id,
        user=current_user,
        new_value=snapshot(opportunity),
    )
    db.refresh(opportunity)
    return _decorate(db, [opportunity])[0]


@router.patch("/{opportunity_id}", response_model=OpportunityOut, summary="Modifier une opportunite")
def update_opportunity(
    opportunity_id: int,
    payload: OpportunityUpdate,
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.update")),
) -> Opportunity:
    opportunity = get_scoped_or_404(
        db, Opportunity, opportunity_id, scope, "Opportunite", write=True
    )
    # Un deplacement vers un autre departement doit rester dans le perimetre.
    if payload.department_id is not None:
        scope.assert_can_write_department(payload.department_id, "une opportunite de ce departement")
    before = snapshot(opportunity)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(opportunity, key, value)
    db.flush()

    _apply_recommendation(db, tenant_id, opportunity)
    _rescore(opportunity)
    db.flush()

    log_update(db, entity_type="opportunity", instance=opportunity, before=before, user=current_user)
    db.refresh(opportunity)
    return _decorate(db, [opportunity])[0]


@router.delete("/{opportunity_id}", status_code=204, response_model=None, summary="Supprimer une opportunite")
def delete_opportunity(
    opportunity_id: int,
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.update")),
) -> None:
    opportunity = get_scoped_or_404(
        db, Opportunity, opportunity_id, scope, "Opportunite", write=True
    )
    log_action(
        db,
        action="delete",
        entity_type="opportunity",
        entity_id=opportunity.id,
        entity_label=opportunity.title,
        organization_id=tenant_id,
        user=current_user,
        old_value=snapshot(opportunity),
    )
    db.delete(opportunity)


# -------------------------------------------------------------------- M4 : qualification
@router.post(
    "/{opportunity_id}/qualify",
    response_model=RecommendationOut,
    summary="M4 - (Re)qualifier : type de solution, justification, alternatives",
)
def qualify_opportunity(
    opportunity_id: int,
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("recommendation.override")),
) -> AIRecommendation:
    opportunity = get_scoped_or_404(db, Opportunity, opportunity_id, scope, "Opportunite")
    before = snapshot(opportunity.recommendation) if opportunity.recommendation else {}
    reco = _apply_recommendation(db, tenant_id, opportunity)
    log_action(
        db,
        action="qualify",
        entity_type="ai_recommendation",
        entity_id=reco.id,
        entity_label=opportunity.title,
        organization_id=tenant_id,
        user=current_user,
        old_value=before or None,
        new_value=snapshot(reco),
    )
    return reco


@router.post(
    "/qualify/simulate",
    summary="M4 - Simuler une qualification sans enregistrer (aide a la saisie)",
)
def simulate_qualification(
    payload: OpportunityCreate,
    current_user: User = Depends(require_permission("recommendation.read")),
) -> dict:
    draft = Opportunity(**payload.model_dump(exclude={"code"}), organization_id=0, code="SIMULATION")
    return recommendation.qualify(draft)


# ---------------------------------------------------------------------- M7 : priorisation
@router.get(
    "/{opportunity_id}/score",
    response_model=ScoreExplanationOut,
    summary="M7 - Detail explicable du score de priorite",
)
def explain_score(
    opportunity_id: int,
    db: DbSession,
    scope: Scope,
    current_user: User = Depends(require_permission("opportunity.read")),
) -> dict:
    opportunity = get_scoped_or_404(db, Opportunity, opportunity_id, scope, "Opportunite")
    return scoring.score_opportunity(opportunity).as_dict()


@router.post(
    "/prioritize",
    response_model=PrioritizeResult,
    summary="M7 - Recalculer le classement du portefeuille (poids parametrables)",
)
def prioritize(
    payload: PrioritizeRequest,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("portfolio.prioritize")),
) -> PrioritizeResult:
    opportunities = list(
        db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique()
    )
    weights = payload.weights.model_dump(exclude_none=True) if payload.weights else None

    if payload.apply_synergies:
        dependencies = list(
            db.scalars(select(Dependency).where(Dependency.organization_id == tenant_id))
        )
        synergy = crossing.synergy_scores(opportunities, dependencies)
        for o in opportunities:
            o.synergies = synergy.get(o.id, o.synergies)

    normalized = scoring.normalize_weights(weights)
    for o in opportunities:
        _rescore(o, weights)

    ordered = scoring.assign_ranks_and_waves(opportunities, wave_size=payload.wave_size)
    db.flush()

    log_action(
        db,
        action="prioritize",
        entity_type="opportunity",
        entity_label=f"{len(ordered)} opportunites reclassees",
        organization_id=tenant_id,
        user=current_user,
        new_value={"weights": normalized, "wave_size": payload.wave_size},
    )

    decorated = _decorate(db, ordered)
    items = [
        PrioritizedItem(
            id=o.id,
            code=o.code,
            title=o.title,
            priority_score=round(float(o.priority_score or 0.0), 1),
            priority_rank=o.priority_rank or 0,
            wave=o.wave or 1,
            department_name=getattr(o, "department_name", None),
            ai_type_label=o.recommendation.ai_type_label if o.recommendation else None,
            phase=o.phase,
            status=o.status,
        )
        for o in decorated
    ]
    return PrioritizeResult(weights=normalized, items=items)
