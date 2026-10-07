"""M9 - Suivi du cycle de vie : projets, phases, jalons, taches, risques, gates."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
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
from app.models.base import ApprovalDecision, Phase, RiskLevel
from app.models.governance import Approval
from app.models.opportunity import Opportunity
from app.models.project import Issue, Milestone, Mitigation, Project, Risk, Stage, Task
from app.schemas.project import (
    GateRequest,
    IssueCreate,
    IssueOut,
    MilestoneCreate,
    MilestoneOut,
    MitigationCreate,
    MitigationOut,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
    RiskCreate,
    RiskOut,
    RiskUpdate,
    StageCreate,
    StageOut,
    TaskCreate,
    TaskOut,
)
from app.services.audit import log_action, log_update, snapshot

router = APIRouter(prefix="/projects", tags=["M9 - Suivi du cycle de vie"])

DEFAULT_STAGES = [
    (Phase.QUALIFICATION, "Qualification", ["Besoin formalise", "Type de solution qualifie"]),
    (Phase.FRAMING, "Cadrage / Business case", ["Business case valide", "Sponsor engage"]),
    (Phase.POC, "POC", ["Faisabilite demontree", "KPI baseline mesure"]),
    (Phase.PILOT, "Pilote", ["Pilote en conditions reelles", "Adoption mesuree"]),
    (Phase.PRODUCTION, "Mise en production", ["Run transfere", "Valeur captee suivie"]),
]


def _serialize_risk(risk: Risk) -> dict:
    data = {c.key: getattr(risk, c.key) for c in risk.__table__.columns}
    data["score"] = risk.score
    data["mitigations"] = risk.mitigations
    return data


# ------------------------------------------------------------------------------ projets
@router.get("", response_model=list[ProjectOut], summary="Lister les projets")
def list_projects(
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("project.read")),
    phase: str | None = None,
    status: str | None = None,
) -> list[Project]:
    stmt = select(Project).where(Project.organization_id == tenant_id)
    if phase:
        stmt = stmt.where(Project.phase == phase)
    if status:
        stmt = stmt.where(Project.status == status)
    # Perimetre departemental : seuls les projets des departements de rattachement.
    stmt = scope.filter_by_department(stmt, Project.department_id)
    return list(db.scalars(stmt.order_by(Project.code)).unique())


@router.post("", response_model=ProjectDetail, status_code=201, summary="Creer un projet (avec ses phases)")
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Project:
    if payload.opportunity_id:
        get_or_404(db, Opportunity, payload.opportunity_id, tenant_id, "Opportunite")

    count = db.scalar(select(func.count(Project.id)).where(Project.organization_id == tenant_id)) or 0
    project = Project(
        organization_id=tenant_id,
        code=payload.code or f"PRJ-2026-{count + 1:03d}",
        **payload.model_dump(exclude={"code"}),
    )
    db.add(project)
    db.flush()

    for index, (code, name, criteria) in enumerate(DEFAULT_STAGES):
        db.add(
            Stage(
                organization_id=tenant_id,
                project_id=project.id,
                code=code,
                name=name,
                sequence=index,
                gate_criteria=criteria,
                status="en_cours" if code == project.phase else "a_faire",
            )
        )
    db.flush()
    db.refresh(project)

    log_action(
        db, action="create", entity_type="project", entity_id=project.id, entity_label=project.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(project),
    )
    return project


@router.get("/{project_id}", response_model=ProjectDetail, summary="Detail d'un projet")
def read_project(
    project_id: int,
    db: DbSession,
    scope: Scope,
    current_user: User = Depends(require_permission("project.read")),
) -> dict:
    project = get_scoped_or_404(db, Project, project_id, scope, "Projet")
    data = {c.key: getattr(project, c.key) for c in project.__table__.columns}
    data["stages"] = sorted(project.stages, key=lambda s: s.sequence)
    data["risks"] = [_serialize_risk(r) for r in project.risks]
    return data


@router.patch("/{project_id}", response_model=ProjectOut, summary="Modifier un projet")
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Project:
    project = get_or_404(db, Project, project_id, tenant_id, "Projet")
    before = snapshot(project)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.flush()
    log_update(db, entity_type="project", instance=project, before=before, user=current_user)
    return project


# -------------------------------------------------------------------------------- gates
@router.post(
    "/{project_id}/gate",
    response_model=ProjectDetail,
    summary="Passer une gate de phase (go / no-go / revision)",
)
def pass_gate(
    project_id: int,
    payload: GateRequest,
    db: DbSession,
    tenant_id: TenantId,
    scope: Scope,
    current_user: User = Depends(require_permission("project.validate_gate")),
) -> dict:
    project = get_scoped_or_404(db, Project, project_id, scope, "Projet", write=True)
    stage = next((s for s in project.stages if s.code == payload.stage_code), None)
    if stage is None:
        raise HTTPException(status_code=404, detail="Phase introuvable sur ce projet")

    before = snapshot(project)
    decision = payload.decision.lower()
    if decision not in ApprovalDecision.ALL:
        raise HTTPException(status_code=422, detail="Decision invalide (go, no_go, revision)")

    ordered = sorted(project.stages, key=lambda s: s.sequence)
    current = next((s for s in ordered if s.code == project.phase), None)

    # Une gate ne se franchit que sur la phase en cours. Sans ce controle, valider une
    # phase deja passee ferait reculer le projet dans le funnel.
    if current is not None and stage.sequence < current.sequence:
        raise HTTPException(
            status_code=409,
            detail=(
                f"La phase '{stage.name}' est deja franchie. "
                f"Le projet est en phase '{current.name}'."
            ),
        )
    if current is not None and stage.sequence > current.sequence:
        raise HTTPException(
            status_code=409,
            detail=(
                f"La phase '{stage.name}' n'est pas encore atteinte. "
                f"Le projet est en phase '{current.name}'."
            ),
        )

    if decision == ApprovalDecision.GO:
        stage.gate_passed = True
        stage.status = "termine"
        stage.end_date = date.today()
        following = next((s for s in ordered if s.sequence > stage.sequence), None)
        if following:
            following.status = "en_cours"
            following.start_date = date.today()
            project.phase = following.code
        else:
            project.phase = Phase.PRODUCTION
            project.status = "termine"
            project.progress = 100.0
    elif decision == ApprovalDecision.NO_GO:
        stage.status = "arrete"
        project.status = "arrete"
    else:
        stage.status = "en_cours"
        stage.gate_passed = False

    db.add(
        Approval(
            organization_id=tenant_id,
            project_id=project.id,
            opportunity_id=project.opportunity_id,
            stage_code=payload.stage_code,
            committee=payload.committee or "Comite IA",
            approver_name=current_user.full_name,
            approver_user_id=current_user.id,
            decision=decision,
            decided_on=date.today(),
            comment=payload.comment,
        )
    )
    db.flush()
    log_update(db, entity_type="project", instance=project, before=before, user=current_user)
    log_action(
        db, action="gate", entity_type="stage", entity_id=stage.id, entity_label=stage.name,
        organization_id=tenant_id, user=current_user,
        new_value={"decision": decision, "comment": payload.comment},
    )

    db.refresh(project)
    data = {c.key: getattr(project, c.key) for c in project.__table__.columns}
    data["stages"] = sorted(project.stages, key=lambda s: s.sequence)
    data["risks"] = [_serialize_risk(r) for r in project.risks]
    return data


# ------------------------------------------------------------------- phases, jalons, taches
@router.post("/stages", response_model=StageOut, status_code=201, summary="Ajouter une phase")
def create_stage(
    payload: StageCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Stage:
    get_or_404(db, Project, payload.project_id, tenant_id, "Projet")
    stage = Stage(organization_id=tenant_id, **payload.model_dump())
    db.add(stage)
    db.flush()
    return stage


@router.get("/{project_id}/milestones", response_model=list[MilestoneOut], summary="Jalons d'un projet")
def list_milestones(
    project_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.read")),
) -> list[Milestone]:
    get_or_404(db, Project, project_id, tenant_id, "Projet")
    return list(
        db.scalars(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.due_date))
    )


@router.post("/milestones", response_model=MilestoneOut, status_code=201, summary="Creer un jalon")
def create_milestone(
    payload: MilestoneCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Milestone:
    get_or_404(db, Project, payload.project_id, tenant_id, "Projet")
    milestone = Milestone(organization_id=tenant_id, **payload.model_dump())
    db.add(milestone)
    db.flush()
    return milestone


@router.get("/{project_id}/tasks", response_model=list[TaskOut], summary="Taches d'un projet")
def list_tasks(
    project_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.read")),
) -> list[Task]:
    get_or_404(db, Project, project_id, tenant_id, "Projet")
    return list(db.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.due_date)))


@router.post("/tasks", response_model=TaskOut, status_code=201, summary="Creer une tache")
def create_task(
    payload: TaskCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Task:
    get_or_404(db, Project, payload.project_id, tenant_id, "Projet")
    task = Task(organization_id=tenant_id, **payload.model_dump())
    db.add(task)
    db.flush()
    return task


# ------------------------------------------------------------------------ risques et issues
@router.get("/risks/all", response_model=list[RiskOut], summary="Tous les risques du portefeuille")
def list_risks(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.read")),
    project_id: int | None = None,
    opportunity_id: int | None = None,
    min_score: int | None = None,
) -> list[dict]:
    stmt = select(Risk).where(Risk.organization_id == tenant_id)
    if project_id:
        stmt = stmt.where(Risk.project_id == project_id)
    if opportunity_id:
        stmt = stmt.where(Risk.opportunity_id == opportunity_id)
    risks = list(db.scalars(stmt).unique())
    if min_score:
        risks = [r for r in risks if r.score >= min_score]
    risks.sort(key=lambda r: -r.score)
    return [_serialize_risk(r) for r in risks]


@router.post("/risks", response_model=RiskOut, status_code=201, summary="Declarer un risque")
def create_risk(
    payload: RiskCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> dict:
    risk = Risk(organization_id=tenant_id, **payload.model_dump())
    risk.severity = RiskLevel.from_score(risk.score)
    db.add(risk)
    db.flush()
    log_action(
        db, action="create", entity_type="risk", entity_id=risk.id, entity_label=risk.title,
        organization_id=tenant_id, user=current_user, new_value=snapshot(risk),
    )
    return _serialize_risk(risk)


@router.patch("/risks/{risk_id}", response_model=RiskOut, summary="Mettre a jour un risque")
def update_risk(
    risk_id: int,
    payload: RiskUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> dict:
    risk = get_or_404(db, Risk, risk_id, tenant_id, "Risque")
    before = snapshot(risk)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(risk, key, value)
    risk.severity = RiskLevel.from_score(risk.score)
    db.flush()
    log_update(db, entity_type="risk", instance=risk, before=before, user=current_user)
    return _serialize_risk(risk)


@router.post("/mitigations", response_model=MitigationOut, status_code=201, summary="Ajouter un plan de mitigation")
def create_mitigation(
    payload: MitigationCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Mitigation:
    get_or_404(db, Risk, payload.risk_id, tenant_id, "Risque")
    mitigation = Mitigation(organization_id=tenant_id, **payload.model_dump())
    db.add(mitigation)
    db.flush()
    return mitigation


@router.get("/{project_id}/issues", response_model=list[IssueOut], summary="Incidents d'un projet")
def list_issues(
    project_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.read")),
) -> list[Issue]:
    get_or_404(db, Project, project_id, tenant_id, "Projet")
    return list(db.scalars(select(Issue).where(Issue.project_id == project_id)))


@router.post("/issues", response_model=IssueOut, status_code=201, summary="Declarer un incident")
def create_issue(
    payload: IssueCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("project.manage")),
) -> Issue:
    get_or_404(db, Project, payload.project_id, tenant_id, "Projet")
    issue = Issue(organization_id=tenant_id, **payload.model_dump())
    db.add(issue)
    db.flush()
    return issue
