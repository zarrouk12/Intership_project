"""M10 - Valeur : couts, benefices, mesures, business case et ROI portefeuille."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, TenantId, get_or_404, require_permission
from app.models.architecture import KPI
from app.models.opportunity import Opportunity
from app.models.organization import Department
from app.models.project import Project
from app.models.value import Benefit, Cost, Measurement
from app.schemas.value import (
    BenefitCreate,
    BenefitOut,
    BusinessCaseOut,
    CostCreate,
    CostOut,
    MeasurementCreate,
    MeasurementOut,
    PortfolioValueOut,
)
from app.services.audit import log_action, snapshot
from app.services.value import aggregate_portfolio_value, compute_value, kpi_progress

router = APIRouter(prefix="/value", tags=["M10 - Valeur & ROI"])


def _scope(model, tenant_id: int, opportunity_id: int | None, project_id: int | None):
    stmt = select(model).where(model.organization_id == tenant_id)
    if opportunity_id:
        stmt = stmt.where(model.opportunity_id == opportunity_id)
    if project_id:
        stmt = stmt.where(model.project_id == project_id)
    return stmt


# --------------------------------------------------------------------------------- couts
@router.get("/costs", response_model=list[CostOut], summary="Lister les couts")
def list_costs(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    opportunity_id: int | None = None,
    project_id: int | None = None,
) -> list[Cost]:
    return list(db.scalars(_scope(Cost, tenant_id, opportunity_id, project_id)))


@router.post("/costs", response_model=CostOut, status_code=201, summary="Ajouter une ligne de cout")
def create_cost(
    payload: CostCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.manage")),
) -> Cost:
    cost = Cost(organization_id=tenant_id, **payload.model_dump())
    db.add(cost)
    db.flush()
    log_action(
        db, action="create", entity_type="cost", entity_id=cost.id, entity_label=cost.label,
        organization_id=tenant_id, user=current_user, new_value=snapshot(cost),
    )
    return cost


# ----------------------------------------------------------------------------- benefices
@router.get("/benefits", response_model=list[BenefitOut], summary="Lister les benefices")
def list_benefits(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    opportunity_id: int | None = None,
    project_id: int | None = None,
) -> list[Benefit]:
    return list(db.scalars(_scope(Benefit, tenant_id, opportunity_id, project_id)))


@router.post("/benefits", response_model=BenefitOut, status_code=201, summary="Ajouter un benefice attendu")
def create_benefit(
    payload: BenefitCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.manage")),
) -> Benefit:
    benefit = Benefit(organization_id=tenant_id, **payload.model_dump())
    db.add(benefit)
    db.flush()
    log_action(
        db, action="create", entity_type="benefit", entity_id=benefit.id, entity_label=benefit.label,
        organization_id=tenant_id, user=current_user, new_value=snapshot(benefit),
    )
    return benefit


# ------------------------------------------------------------------------------- mesures
@router.get("/measurements", response_model=list[MeasurementOut], summary="Relevés de KPI")
def list_measurements(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    kpi_id: int | None = None,
) -> list[Measurement]:
    stmt = select(Measurement).where(Measurement.organization_id == tenant_id)
    if kpi_id:
        stmt = stmt.where(Measurement.kpi_id == kpi_id)
    return list(db.scalars(stmt.order_by(Measurement.measured_on)))


@router.post("/measurements", response_model=MeasurementOut, status_code=201, summary="Enregistrer un releve")
def create_measurement(
    payload: MeasurementCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.manage")),
) -> Measurement:
    kpi = get_or_404(db, KPI, payload.kpi_id, tenant_id, "KPI")
    measurement = Measurement(organization_id=tenant_id, **payload.model_dump())
    db.add(measurement)
    kpi.current_value = payload.value
    db.flush()
    log_action(
        db, action="measure", entity_type="kpi", entity_id=kpi.id, entity_label=kpi.name,
        organization_id=tenant_id, user=current_user,
        new_value={"value": payload.value, "measured_on": payload.measured_on.isoformat()},
    )
    return measurement


# ------------------------------------------------------------------------- business case
@router.get(
    "/business-case/{opportunity_id}",
    response_model=BusinessCaseOut,
    summary="Business case d'une opportunite (TCO, ROI, payback, impact P&L)",
)
def business_case(
    opportunity_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    horizon_years: int = Query(default=3, ge=1, le=10),
) -> dict:
    get_or_404(db, Opportunity, opportunity_id, tenant_id, "Opportunite")
    costs = list(db.scalars(_scope(Cost, tenant_id, opportunity_id, None)))
    benefits = list(db.scalars(_scope(Benefit, tenant_id, opportunity_id, None)))
    summary = compute_value(costs, benefits, horizon_years=horizon_years)
    return {**summary.as_dict(), "costs": costs, "benefits": benefits}


@router.get("/portfolio", response_model=PortfolioValueOut, summary="ROI consolide du portefeuille")
def portfolio_value(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    horizon_years: int = Query(default=3, ge=1, le=10),
) -> dict:
    opportunities = list(db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique())
    costs = list(db.scalars(select(Cost).where(Cost.organization_id == tenant_id)))
    benefits = list(db.scalars(select(Benefit).where(Benefit.organization_id == tenant_id)))

    summaries = []
    for opportunity in opportunities:
        o_costs = [c for c in costs if c.opportunity_id == opportunity.id]
        o_benefits = [b for b in benefits if b.opportunity_id == opportunity.id]
        if o_costs or o_benefits:
            summaries.append(compute_value(o_costs, o_benefits, horizon_years=horizon_years))
    return aggregate_portfolio_value(summaries)


@router.get("/dashboard", summary="M11 - Donnees de l'ecran Valeur & ROI")
def value_dashboard(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    horizon_years: int = Query(default=3, ge=1, le=10),
) -> dict:
    opportunities = list(db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique())
    costs = list(db.scalars(select(Cost).where(Cost.organization_id == tenant_id)))
    benefits = list(db.scalars(select(Benefit).where(Benefit.organization_id == tenant_id)))
    kpis = list(db.scalars(select(KPI).where(KPI.organization_id == tenant_id)))
    departments = {d.id: d.name for d in db.scalars(select(Department).where(Department.organization_id == tenant_id))}

    summaries = []
    ranking = []
    by_department: dict[str, dict] = {}

    for opportunity in opportunities:
        o_costs = [c for c in costs if c.opportunity_id == opportunity.id]
        o_benefits = [b for b in benefits if b.opportunity_id == opportunity.id]
        if not (o_costs or o_benefits):
            continue
        summary = compute_value(o_costs, o_benefits, horizon_years=horizon_years)
        summaries.append(summary)
        ranking.append(
            {
                "id": opportunity.id,
                "code": opportunity.code,
                "title": opportunity.title,
                "department_name": departments.get(opportunity.department_id),
                "tco_eur": round(summary.tco_eur, 0),
                "annual_benefit_eur": round(summary.annual_benefit_eur, 0),
                "roi_percent": round(summary.roi_percent, 1),
                "payback_months": round(summary.payback_months, 1) if summary.payback_months else None,
            }
        )
        dept = departments.get(opportunity.department_id) or "Non affecte"
        bucket = by_department.setdefault(
            dept, {"department": dept, "tco_eur": 0.0, "annual_benefit_eur": 0.0, "count": 0}
        )
        bucket["tco_eur"] += summary.tco_eur
        bucket["annual_benefit_eur"] += summary.annual_benefit_eur
        bucket["count"] += 1

    ranking.sort(key=lambda r: -r["roi_percent"])
    for bucket in by_department.values():
        bucket["tco_eur"] = round(bucket["tco_eur"], 0)
        bucket["annual_benefit_eur"] = round(bucket["annual_benefit_eur"], 0)
        bucket["roi_percent"] = (
            round((bucket["annual_benefit_eur"] * horizon_years - bucket["tco_eur"]) / bucket["tco_eur"] * 100, 1)
            if bucket["tco_eur"]
            else 0.0
        )

    return {
        "portfolio": aggregate_portfolio_value(summaries),
        "kpis": [kpi_progress(k) for k in kpis if k.baseline_value is not None],
        "by_department": sorted(by_department.values(), key=lambda b: -b["annual_benefit_eur"]),
        "roi_ranking": ranking[:12],
    }
