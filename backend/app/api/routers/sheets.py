"""M8 - Fiche projet : generation, versions, validation comite, export."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, TenantId, get_or_404, require_permission
from app.models.architecture import KPI
from app.models.base import ApprovalDecision
from app.models.governance import Approval, Document, Version
from app.models.opportunity import Opportunity
from app.models.project import Project, Risk
from app.models.value import Benefit, Cost
from app.schemas.governance import (
    ApprovalCreate,
    ApprovalOut,
    DocumentDetail,
    DocumentOut,
    GenerateSheetRequest,
    VersionOut,
)
from app.services import scoring
from app.services.audit import log_action, snapshot
from app.services.value import compute_value, kpi_progress

router = APIRouter(prefix="/sheets", tags=["M8 - Fiche projet"])


def _build_sheet(db, tenant_id: int, opportunity: Opportunity) -> dict:
    """Assemble le contenu complet de la fiche projet a partir des donnees vivantes."""
    costs = list(
        db.scalars(
            select(Cost).where(Cost.organization_id == tenant_id, Cost.opportunity_id == opportunity.id)
        )
    )
    benefits = list(
        db.scalars(
            select(Benefit).where(
                Benefit.organization_id == tenant_id, Benefit.opportunity_id == opportunity.id
            )
        )
    )
    kpis = list(
        db.scalars(select(KPI).where(KPI.organization_id == tenant_id, KPI.opportunity_id == opportunity.id))
    )
    risks = list(
        db.scalars(select(Risk).where(Risk.organization_id == tenant_id, Risk.opportunity_id == opportunity.id))
    )
    project = db.scalar(select(Project).where(Project.opportunity_id == opportunity.id))
    value = compute_value(costs, benefits)
    breakdown = scoring.score_opportunity(opportunity)
    reco = opportunity.recommendation

    total = db.scalar(
        select(Opportunity.id).where(Opportunity.organization_id == tenant_id).order_by(Opportunity.id)
    )
    portfolio_size = len(
        list(db.scalars(select(Opportunity.id).where(Opportunity.organization_id == tenant_id)))
    )

    return {
        "code": opportunity.code,
        "title": opportunity.title,
        "generated_on": date.today().isoformat(),
        "identity": {
            "department_id": opportunity.department_id,
            "sponsor": opportunity.sponsor,
            "business_owner": opportunity.business_owner,
            "technical_owner": opportunity.technical_owner,
            "phase": opportunity.phase,
            "status": opportunity.status,
        },
        "as_is": {
            "context": opportunity.as_is_context,
            "pain_points": opportunity.pain_points,
            "desired_outcome": opportunity.desired_outcome,
        },
        "recommendation": {
            "ai_type": reco.ai_type if reco else None,
            "ai_type_label": reco.ai_type_label if reco else None,
            "solution_pattern": reco.solution_pattern if reco else None,
            "rationale": reco.rationale if reco else None,
            "confidence": reco.confidence if reco else None,
            "alternatives": reco.alternatives if reco else [],
            "guardrails": reco.guardrails if reco else [],
            "fired_rules": reco.fired_rules if reco else [],
        },
        "kpis": [kpi_progress(k) for k in kpis],
        "business_case": value.as_dict(),
        "costs": [{"label": c.label, "amount_eur": c.amount_eur, "recurring": c.recurring} for c in costs],
        "benefits": [
            {"label": b.label, "annual_amount_eur": b.annual_amount_eur, "pnl_line": b.pnl_line}
            for b in benefits
        ],
        "risks": [
            {
                "title": r.title,
                "category": r.category,
                "probability": r.probability,
                "impact": r.impact,
                "score": r.score,
                "severity": r.severity,
                "mitigations": [m.action for m in r.mitigations],
            }
            for r in sorted(risks, key=lambda r: -r.score)
        ],
        "priority": {
            **breakdown.as_dict(),
            "rank": opportunity.priority_rank,
            "portfolio_size": portfolio_size,
            "wave": opportunity.wave,
        },
        "project": {
            "code": project.code if project else None,
            "next_gate_label": project.next_gate_label if project else None,
            "next_gate_date": project.next_gate_date.isoformat()
            if project and project.next_gate_date
            else None,
        },
    }


@router.get("", response_model=list[DocumentOut], summary="Lister les fiches projet")
def list_sheets(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.read")),
    opportunity_id: int | None = None,
) -> list[Document]:
    stmt = select(Document).where(Document.organization_id == tenant_id)
    if opportunity_id:
        stmt = stmt.where(Document.opportunity_id == opportunity_id)
    return list(db.scalars(stmt.order_by(Document.code)).unique())


@router.get("/opportunity/{opportunity_id}/preview", summary="Previsualiser la fiche sans la versionner")
def preview_sheet(
    opportunity_id: int, db: DbSession, tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.read")),
) -> dict:
    opportunity = get_or_404(db, Opportunity, opportunity_id, tenant_id, "Opportunite")
    return _build_sheet(db, tenant_id, opportunity)


@router.post(
    "/opportunity/{opportunity_id}/generate",
    response_model=DocumentDetail,
    status_code=201,
    summary="Generer une nouvelle version de la fiche projet",
)
def generate_sheet(
    opportunity_id: int,
    payload: GenerateSheetRequest,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.write")),
) -> Document:
    opportunity = get_or_404(db, Opportunity, opportunity_id, tenant_id, "Opportunite")
    content = _build_sheet(db, tenant_id, opportunity)

    document = db.scalar(
        select(Document).where(
            Document.organization_id == tenant_id,
            Document.opportunity_id == opportunity.id,
            Document.doc_type == "fiche_projet",
        )
    )
    if document is None:
        document = Document(
            organization_id=tenant_id,
            opportunity_id=opportunity.id,
            code=f"FICHE-{opportunity.code}",
            title=f"Fiche projet - {opportunity.title}",
            doc_type="fiche_projet",
            status="brouillon",
            current_version=0,
            author=current_user.full_name,
        )
        db.add(document)
        db.flush()

    document.current_version += 1
    version = Version(
        organization_id=tenant_id,
        document_id=document.id,
        number=document.current_version,
        label=payload.label or f"v{document.current_version}",
        content=content,
        change_summary=payload.change_summary or "Generation automatique depuis les donnees courantes",
        created_by=current_user.full_name,
    )
    db.add(version)
    db.flush()

    log_action(
        db,
        action="generate",
        entity_type="document",
        entity_id=document.id,
        entity_label=document.title,
        organization_id=tenant_id,
        user=current_user,
        new_value={"version": document.current_version},
    )
    db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentDetail, summary="Detail d'une fiche et de ses versions")
def read_sheet(
    document_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.read")),
) -> Document:
    return get_or_404(db, Document, document_id, tenant_id, "Fiche projet")


@router.get("/{document_id}/versions/{number}", response_model=VersionOut, summary="Lire une version precise")
def read_version(
    document_id: int, number: int, db: DbSession, tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.read")),
) -> Version:
    document = get_or_404(db, Document, document_id, tenant_id, "Fiche projet")
    version = next((v for v in document.versions if v.number == number), None)
    if version is None:
        raise HTTPException(status_code=404, detail="Version introuvable")
    return version


@router.post(
    "/{document_id}/approvals",
    response_model=ApprovalOut,
    status_code=201,
    summary="Enregistrer une decision de comite",
)
def approve_sheet(
    document_id: int,
    payload: ApprovalCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.approve")),
) -> Approval:
    document = get_or_404(db, Document, document_id, tenant_id, "Fiche projet")
    decision = payload.decision.lower()
    if decision not in ApprovalDecision.ALL:
        raise HTTPException(status_code=422, detail="Decision invalide (en_attente, go, no_go, revision)")

    approval = Approval(
        organization_id=tenant_id,
        document_id=document.id,
        opportunity_id=document.opportunity_id,
        project_id=payload.project_id,
        stage_code=payload.stage_code,
        committee=payload.committee or "Comite IA",
        approver_name=payload.approver_name or current_user.full_name,
        approver_user_id=current_user.id,
        decision=decision,
        decided_on=payload.decided_on or date.today(),
        comment=payload.comment,
    )
    db.add(approval)

    before = snapshot(document)
    document.status = {
        ApprovalDecision.GO: "approuve",
        ApprovalDecision.NO_GO: "rejete",
        ApprovalDecision.REVISION: "en_revision",
        ApprovalDecision.PENDING: "soumis",
    }[decision]

    if document.opportunity_id and decision == ApprovalDecision.GO:
        opportunity = db.get(Opportunity, document.opportunity_id)
        if opportunity:
            opportunity.status = "approuve"

    db.flush()
    log_action(
        db,
        action="approve",
        entity_type="document",
        entity_id=document.id,
        entity_label=document.title,
        organization_id=tenant_id,
        user=current_user,
        old_value={"status": before.get("status")},
        new_value={"status": document.status, "decision": decision, "comment": payload.comment},
    )
    return approval


@router.get(
    "/opportunity/{opportunity_id}/export",
    summary="Exporter la fiche projet (format json ou html imprimable en PDF)",
    response_class=JSONResponse,
)
def export_sheet(
    opportunity_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("sheet.read")),
    format: str = "json",
):
    opportunity = get_or_404(db, Opportunity, opportunity_id, tenant_id, "Opportunite")
    content = _build_sheet(db, tenant_id, opportunity)

    if format.lower() == "json":
        return JSONResponse(
            content=content,
            headers={"Content-Disposition": f'attachment; filename="{opportunity.code}.json"'},
        )

    if format.lower() not in {"html", "pdf", "word", "docx"}:
        raise HTTPException(status_code=422, detail="Format supporte : json, html")

    bc = content["business_case"]
    rows_kpi = "".join(
        f"<tr><td>{k['name']}</td><td>{k['baseline_value']} {k['unit'] or ''}</td>"
        f"<td>{k['target_value']} {k['unit'] or ''}</td></tr>"
        for k in content["kpis"]
    )
    rows_risk = "".join(
        f"<tr><td>{r['title']}</td><td>{r['severity']}</td><td>{r['score']}</td></tr>"
        for r in content["risks"]
    )
    reco = content["recommendation"]
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{content['code']} - {content['title']}</title>
<style>
 body{{font-family:'IBM Plex Sans',Arial,sans-serif;color:#16241E;margin:40px;}}
 h1{{font-family:Georgia,serif;font-size:26px;margin-bottom:4px;}}
 h2{{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:#5E6F67;margin-top:28px;}}
 table{{border-collapse:collapse;width:100%;margin-top:8px;}}
 td,th{{border:1px solid #E1E8E4;padding:8px 10px;text-align:left;font-size:13px;}}
 .kpi{{display:inline-block;border:1px solid #E1E8E4;border-radius:10px;padding:12px 18px;margin:6px 8px 0 0;}}
 .kpi b{{display:block;font-size:20px;color:#157F5C;}}
</style></head><body>
<h1>{content['title']}</h1>
<p>{content['code']} &middot; genere le {content['generated_on']} &middot; phase {content['identity']['phase']}</p>
<h2>Contexte AS-IS</h2><p>{content['as_is']['context'] or '-'}</p>
<h2>Solution recommandee</h2>
<p><b>{reco['ai_type_label'] or '-'}</b> &mdash; {reco['solution_pattern'] or ''}</p>
<p>{reco['rationale'] or ''}</p>
<h2>KPI et benefice</h2>
<table><tr><th>Indicateur</th><th>Baseline</th><th>Cible</th></tr>{rows_kpi}</table>
<h2>Business case</h2>
<div class="kpi"><b>{bc['tco_eur']:,.0f} EUR</b>TCO {bc['horizon_years']} ans</div>
<div class="kpi"><b>{bc['annual_benefit_eur']:,.0f} EUR</b>Gains annuels</div>
<div class="kpi"><b>{bc['roi_percent']} %</b>ROI</div>
<div class="kpi"><b>{bc['payback_months'] or '-'} mois</b>Payback</div>
<h2>Risques</h2>
<table><tr><th>Risque</th><th>Severite</th><th>Score</th></tr>{rows_risk}</table>
<h2>Score de priorite</h2>
<p><b>{content['priority']['priority_score']}</b> / 100 &middot; rang {content['priority']['rank'] or '-'}
 sur {content['priority']['portfolio_size']} &middot; vague {content['priority']['wave'] or '-'}</p>
</body></html>"""
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="{opportunity.code}.html"'},
    )
