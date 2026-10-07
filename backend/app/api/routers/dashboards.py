"""M11 - Endpoints d'agregation pour les tableaux de bord."""
from __future__ import annotations

from fastapi import Depends, APIRouter
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, Scope, TenantId, require_permission
from app.models.architecture import KPI
from app.models.base import Phase
from app.models.diagnostic import Assessment
from app.models.opportunity import Opportunity
from app.models.organization import Department
from app.models.project import Project, Risk
from app.models.value import Benefit, Cost
from app.schemas.dashboard import DirectionDashboard
from app.services import scoring
from app.services.readiness import compute_readiness
from app.services.value import aggregate_portfolio_value, compute_value, kpi_progress

router = APIRouter(prefix="/dashboards", tags=["M11 - Tableaux de bord"])


def _millions(amount: float) -> str:
    """Montant compact a la francaise : 3,1 M EUR / 240 k EUR."""
    if abs(amount) >= 1_000_000:
        return f"{amount / 1_000_000:.1f}".replace(".", ",") + " M€"
    if abs(amount) >= 1_000:
        return f"{amount / 1_000:.0f} k€"
    return f"{amount:.0f} €"


@router.get("/direction", response_model=DirectionDashboard, summary="Tableau de bord Direction")
def direction_dashboard(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("dashboard.direction")),
) -> dict:
    opportunities = list(
        db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique()
    )
    projects = list(db.scalars(select(Project).where(Project.organization_id == tenant_id)).unique())
    risks = list(db.scalars(select(Risk).where(Risk.organization_id == tenant_id)).unique())
    costs = list(db.scalars(select(Cost).where(Cost.organization_id == tenant_id)))
    benefits = list(db.scalars(select(Benefit).where(Benefit.organization_id == tenant_id)))
    departments = {
        d.id: d.name
        for d in db.scalars(select(Department).where(Department.organization_id == tenant_id))
    }

    # --- Valeur consolidee ---
    summaries = []
    for opportunity in opportunities:
        o_costs = [c for c in costs if c.opportunity_id == opportunity.id]
        o_benefits = [b for b in benefits if b.opportunity_id == opportunity.id]
        if o_costs or o_benefits:
            summaries.append(compute_value(o_costs, o_benefits))
    portfolio = aggregate_portfolio_value(summaries)

    budget = sum(float(p.budget_eur or 0.0) for p in projects)
    committed = sum(float(p.committed_eur or 0.0) for p in projects)
    if budget == 0.0:
        budget = sum(float(o.estimated_cost_eur or 0.0) for o in opportunities)
        committed = portfolio["tco_eur"]

    critical_risks = [r for r in risks if r.score >= 16]
    pending_risks = [r for r in critical_risks if r.status == "en_attente"]
    # Le funnel va de l'opportunite a la production : tout ce qui n'est pas rejete est actif.
    active = [o for o in opportunities if o.status != "rejete"]
    launched_this_quarter = [o for o in opportunities if o.phase in (Phase.POC, Phase.PILOT)]

    kpis = [
        {
            "key": "active_projects",
            "label": "Projets actifs",
            "value": float(len(active)),
            "unit": None,
            "hint": f"+{len(launched_this_quarter)} ce trimestre",
            "trend": "up",
            "tone": "neutral",
        },
        {
            "key": "investment",
            "label": "Investissement",
            "value": round(committed, 0),
            "unit": "EUR",
            "hint": f"Engagé sur {_millions(budget)} budgétés",
            "tone": "neutral",
        },
        {
            "key": "roi",
            "label": "ROI portefeuille",
            "value": portfolio["roi_percent"],
            "unit": "%",
            "hint": (
                f"Payback moyen {portfolio['average_payback_months']:.0f} mois"
                if portfolio["average_payback_months"]
                else "Payback non calculé"
            ),
            "tone": "positive",
        },
        {
            "key": "critical_risks",
            "label": "Risques critiques",
            "value": float(len(critical_risks)),
            "unit": None,
            "hint": f"{len(pending_risks)} en attente de validation",
            "tone": "negative",
        },
    ]

    # --- Repartition par phase TOGAF ---
    total = len(opportunities) or 1
    counts = {code: 0 for code in Phase.ALL}
    for opportunity in opportunities:
        counts[opportunity.phase] = counts.get(opportunity.phase, 0) + 1
    phases = [
        {
            "code": code,
            "label": Phase.LABELS[code],
            "count": counts.get(code, 0),
            "share": round(counts.get(code, 0) / total * 100, 1),
        }
        for code in Phase.ALL
    ]

    # --- Top priorites ---
    ordered = sorted(opportunities, key=lambda o: -(o.priority_score or 0.0))
    risk_by_opp: dict[int, int] = {}
    for r in risks:
        if r.opportunity_id:
            risk_by_opp[r.opportunity_id] = max(risk_by_opp.get(r.opportunity_id, 0), r.score)

    top = [
        {
            "id": o.id,
            "code": o.code,
            "title": o.title,
            "department_name": departments.get(o.department_id),
            "ai_type": o.recommendation.ai_type if o.recommendation else None,
            "ai_type_label": o.recommendation.ai_type_label if o.recommendation else None,
            "phase": o.phase,
            "phase_label": Phase.LABELS.get(o.phase, o.phase),
            "status": o.status,
            "priority_score": round(float(o.priority_score or 0.0), 1),
            "priority_rank": o.priority_rank,
            "expected_benefit_eur": float(o.expected_benefit_eur or 0.0),
            "risk_score": risk_by_opp.get(o.id, o.risk_probability * o.risk_impact),
        }
        for o in ordered[:6]
    ]

    # --- Readiness consolide ---
    assessments = list(db.scalars(select(Assessment).where(Assessment.organization_id == tenant_id)))
    readiness_global = None
    if assessments:
        responses = [r for a in assessments for r in a.responses]
        if responses:
            readiness_global = round(compute_readiness(responses).global_score, 1)

    return {
        "kpis": kpis,
        "matrix": scoring.portfolio_matrix(opportunities),
        "phases": phases,
        "top_priorities": top,
        "readiness_global": readiness_global,
        "total_opportunities": len(opportunities),
    }


@router.get("/portfolio", summary="Table complete du portefeuille (filtrable cote client)")
def portfolio_table(
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("portfolio.read")),
) -> list[dict]:
    stmt = scope.filter_by_department(
        select(Opportunity).where(Opportunity.organization_id == tenant_id),
        Opportunity.department_id,
    )
    opportunities = list(db.scalars(stmt).unique())
    departments = {
        d.id: d.name
        for d in db.scalars(select(Department).where(Department.organization_id == tenant_id))
    }
    risks = list(db.scalars(select(Risk).where(Risk.organization_id == tenant_id)).unique())
    risk_by_opp: dict[int, int] = {}
    for r in risks:
        if r.opportunity_id:
            risk_by_opp[r.opportunity_id] = max(risk_by_opp.get(r.opportunity_id, 0), r.score)

    rows = [
        {
            "id": o.id,
            "code": o.code,
            "title": o.title,
            "department_name": departments.get(o.department_id),
            "ai_type": o.recommendation.ai_type if o.recommendation else None,
            "ai_type_label": o.recommendation.ai_type_label if o.recommendation else None,
            "phase": o.phase,
            "phase_label": Phase.LABELS.get(o.phase, o.phase),
            "status": o.status,
            "priority_score": round(float(o.priority_score or 0.0), 1),
            "priority_rank": o.priority_rank,
            "wave": o.wave,
            "expected_benefit_eur": float(o.expected_benefit_eur or 0.0),
            "estimated_cost_eur": float(o.estimated_cost_eur or 0.0),
            "risk_score": risk_by_opp.get(o.id, o.risk_probability * o.risk_impact),
        }
        for o in opportunities
    ]
    rows.sort(key=lambda r: -r["priority_score"])
    return rows


@router.get("/kpis", summary="KPI suivis avec leur avancement baseline -> cible")
def kpi_overview(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
) -> list[dict]:
    from app.services.value import kpi_progress

    kpis = list(db.scalars(select(KPI).where(KPI.organization_id == tenant_id)))
    return [kpi_progress(k) for k in kpis]

@router.get(
    "/department",
    summary="M11 - Tableau de bord de departement, restreint au perimetre de l'utilisateur",
)
def department_dashboard(
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("dashboard.department")),
) -> dict:
    """Vue d'un responsable de departement.

    Contrairement au tableau de bord Direction, les agregats ne portent que sur les
    departements de rattachement : un responsable Commercial ne voit pas les chiffres
    de la Production. Un utilisateur au perimetre organisation voit tous les
    departements, ce qui rend cet ecran utilisable par la Direction comme par un
    responsable.
    """
    opp_stmt = scope.filter_by_department(
        select(Opportunity).where(Opportunity.organization_id == tenant_id),
        Opportunity.department_id,
    )
    opportunities = list(db.scalars(opp_stmt).unique())

    project_stmt = scope.filter_by_department(
        select(Project).where(Project.organization_id == tenant_id), Project.department_id
    )
    projects = list(db.scalars(project_stmt).unique())

    departments = {
        d.id: d.name
        for d in db.scalars(select(Department).where(Department.organization_id == tenant_id))
    }
    opportunity_ids = {o.id for o in opportunities}
    project_ids = {p.id for p in projects}

    risks = [
        r
        for r in db.scalars(select(Risk).where(Risk.organization_id == tenant_id)).unique()
        if (r.opportunity_id in opportunity_ids) or (r.project_id in project_ids)
    ]

    costs = [
        c
        for c in db.scalars(select(Cost).where(Cost.organization_id == tenant_id))
        if c.opportunity_id in opportunity_ids
    ]
    benefits = [
        b
        for b in db.scalars(select(Benefit).where(Benefit.organization_id == tenant_id))
        if b.opportunity_id in opportunity_ids
    ]

    summaries = []
    for opportunity in opportunities:
        o_costs = [c for c in costs if c.opportunity_id == opportunity.id]
        o_benefits = [b for b in benefits if b.opportunity_id == opportunity.id]
        if o_costs or o_benefits:
            summaries.append(compute_value(o_costs, o_benefits))
    portfolio = aggregate_portfolio_value(summaries)

    counts = {code: 0 for code in Phase.ALL}
    for opportunity in opportunities:
        counts[opportunity.phase] = counts.get(opportunity.phase, 0) + 1
    total = len(opportunities) or 1

    kpis = [
        k
        for k in db.scalars(select(KPI).where(KPI.organization_id == tenant_id))
        if k.opportunity_id in opportunity_ids
    ]

    scope_names = (
        sorted(departments.get(d, str(d)) for d in scope.department_ids)
        if not scope.is_organization_wide
        else sorted(departments.values())
    )

    ordered = sorted(opportunities, key=lambda o: -(o.priority_score or 0.0))
    return {
        "scope": {**scope.as_dict(), "department_names": scope_names},
        "kpis": [
            {
                "key": "opportunities",
                "label": "Opportunités du périmètre",
                "value": float(len(opportunities)),
                "unit": None,
                "hint": ", ".join(scope_names[:3]) or "Aucun département rattaché",
                "tone": "neutral",
            },
            {
                "key": "active_projects",
                "label": "Projets actifs",
                "value": float(len([p for p in projects if p.status == "actif"])),
                "unit": None,
                "hint": f"{len(projects)} projets au total",
                "tone": "neutral",
            },
            {
                "key": "annual_benefit",
                "label": "Gains annuels attendus",
                "value": portfolio["annual_benefit_eur"],
                "unit": "EUR",
                "hint": f"TCO {_millions(portfolio['tco_eur'])}",
                "tone": "positive",
            },
            {
                "key": "open_risks",
                "label": "Risques ouverts",
                "value": float(len([r for r in risks if r.status == "ouvert"])),
                "unit": None,
                "hint": f"{len([r for r in risks if r.score >= 16])} critiques",
                "tone": "negative",
            },
        ],
        "phases": [
            {
                "code": code,
                "label": Phase.LABELS[code],
                "count": counts.get(code, 0),
                "share": round(counts.get(code, 0) / total * 100, 1),
            }
            for code in Phase.ALL
        ],
        "opportunities": [
            {
                "id": o.id,
                "code": o.code,
                "title": o.title,
                "department_name": departments.get(o.department_id),
                "ai_type_label": o.recommendation.ai_type_label if o.recommendation else None,
                "phase": o.phase,
                "phase_label": Phase.LABELS.get(o.phase, o.phase),
                "status": o.status,
                "priority_score": round(float(o.priority_score or 0.0), 1),
                "priority_rank": o.priority_rank,
                "expected_benefit_eur": float(o.expected_benefit_eur or 0.0),
                "risk_score": o.risk_probability * o.risk_impact,
            }
            for o in ordered[:8]
        ],
        "projects": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "phase": p.phase,
                "phase_label": Phase.LABELS.get(p.phase, p.phase),
                "status": p.status,
                "progress": float(p.progress or 0.0),
                "next_gate_label": p.next_gate_label,
                "next_gate_date": p.next_gate_date.isoformat() if p.next_gate_date else None,
            }
            for p in sorted(projects, key=lambda x: -(x.progress or 0.0))[:8]
        ],
        "kpi_progress": [kpi_progress(k) for k in kpis if k.baseline_value is not None],
        "risks": [
            {
                "id": r.id,
                "title": r.title,
                "category": r.category,
                "score": r.score,
                "severity": r.severity,
                "status": r.status,
            }
            for r in sorted(risks, key=lambda r: -r.score)[:6]
        ],
    }
