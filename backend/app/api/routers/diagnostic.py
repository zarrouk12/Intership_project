"""M2 / M5 - Diagnostic AS-IS et calcul de readiness."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, TenantId, get_or_404, require_permission
from app.models.diagnostic import Assessment, AssessmentResponse
from app.schemas.diagnostic import (
    AssessmentCreate,
    AssessmentDetail,
    AssessmentOut,
    AssessmentResponseCreate,
    AssessmentResponseOut,
    AssessmentResponseUpdate,
    AssessmentUpdate,
    ReadinessOut,
)
from app.services.audit import log_action, log_update, snapshot
from app.services.readiness import compute_for_assessment, compute_readiness

router = APIRouter(prefix="/diagnostic", tags=["M2/M5 - Diagnostic & Readiness"])


@router.get("/assessments", response_model=list[AssessmentOut], summary="Lister les campagnes")
def list_assessments(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.read")),
    site_id: int | None = None,
) -> list[Assessment]:
    stmt = select(Assessment).where(Assessment.organization_id == tenant_id)
    if site_id:
        stmt = stmt.where(Assessment.site_id == site_id)
    return list(db.scalars(stmt.order_by(Assessment.created_at.desc())))


@router.post("/assessments", response_model=AssessmentDetail, status_code=201, summary="Creer une campagne")
def create_assessment(
    payload: AssessmentCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.answer")),
) -> Assessment:
    data = payload.model_dump(exclude={"responses"})
    assessment = Assessment(organization_id=tenant_id, **data)
    db.add(assessment)
    db.flush()

    for response in payload.responses:
        db.add(
            AssessmentResponse(
                organization_id=tenant_id, assessment_id=assessment.id, **response.model_dump()
            )
        )
    db.flush()
    db.refresh(assessment)

    log_action(
        db,
        action="create",
        entity_type="assessment",
        entity_id=assessment.id,
        entity_label=assessment.name,
        organization_id=tenant_id,
        user=current_user,
        new_value=snapshot(assessment),
    )
    return assessment


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetail, summary="Detail d'une campagne")
def read_assessment(
    assessment_id: int, db: DbSession, tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.read")),
) -> Assessment:
    return get_or_404(db, Assessment, assessment_id, tenant_id, "Campagne de diagnostic")


@router.patch("/assessments/{assessment_id}", response_model=AssessmentOut, summary="Modifier une campagne")
def update_assessment(
    assessment_id: int,
    payload: AssessmentUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.answer")),
) -> Assessment:
    assessment = get_or_404(db, Assessment, assessment_id, tenant_id, "Campagne de diagnostic")
    before = snapshot(assessment)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, key, value)
    db.flush()
    log_update(db, entity_type="assessment", instance=assessment, before=before, user=current_user)
    return assessment


@router.post(
    "/assessments/{assessment_id}/responses",
    response_model=AssessmentResponseOut,
    status_code=201,
    summary="Ajouter une reponse de diagnostic",
)
def add_response(
    assessment_id: int,
    payload: AssessmentResponseCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.answer")),
) -> AssessmentResponse:
    assessment = get_or_404(db, Assessment, assessment_id, tenant_id, "Campagne de diagnostic")
    response = AssessmentResponse(
        organization_id=tenant_id, assessment_id=assessment.id, **payload.model_dump()
    )
    db.add(response)
    db.flush()
    log_action(
        db,
        action="create",
        entity_type="assessment_response",
        entity_id=response.id,
        entity_label=response.dimension_label,
        organization_id=tenant_id,
        user=current_user,
        new_value=snapshot(response),
    )
    return response


@router.patch(
    "/responses/{response_id}",
    response_model=AssessmentResponseOut,
    summary="Modifier une reponse (note, poids, confiance, preuve)",
)
def update_response(
    response_id: int,
    payload: AssessmentResponseUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.answer")),
) -> AssessmentResponse:
    response = get_or_404(db, AssessmentResponse, response_id, tenant_id, "Reponse de diagnostic")
    before = snapshot(response)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(response, key, value)
    db.flush()
    log_update(
        db,
        entity_type="assessment_response",
        instance=response,
        before=before,
        user=current_user,
        label=response.dimension_label,
    )
    return response


@router.get(
    "/assessments/{assessment_id}/readiness",
    response_model=ReadinessOut,
    summary="Score de readiness detaille et dimensions bloquantes",
)
def assessment_readiness(
    assessment_id: int, db: DbSession, tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.read")),
) -> dict:
    assessment = get_or_404(db, Assessment, assessment_id, tenant_id, "Campagne de diagnostic")
    return compute_for_assessment(assessment).as_dict()


@router.get(
    "/readiness",
    response_model=ReadinessOut,
    summary="Readiness consolide de l'organisation (toutes campagnes ou un site)",
)
def global_readiness(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("diagnostic.read")),
    site_id: int | None = Query(default=None),
    assessment_id: int | None = Query(default=None),
) -> dict:
    stmt = select(Assessment).where(Assessment.organization_id == tenant_id)
    if assessment_id:
        stmt = stmt.where(Assessment.id == assessment_id)
    if site_id:
        stmt = stmt.where(Assessment.site_id == site_id)
    assessments = list(db.scalars(stmt))
    if not assessments:
        raise HTTPException(status_code=404, detail="Aucune campagne de diagnostic trouvee")

    responses = [r for a in assessments for r in a.responses]
    threshold = min(float(a.blocking_threshold or 2.5) for a in assessments)
    return compute_readiness(responses, blocking_threshold=threshold).as_dict()
