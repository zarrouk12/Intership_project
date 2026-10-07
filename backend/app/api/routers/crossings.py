"""M6 - Croisements interservices : referentiels partages, dependances, doublons."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, TenantId, get_or_404, require_permission
from app.models.architecture import KPI, Application, DataSource, Process
from app.models.opportunity import Dependency, Opportunity
from app.schemas.architecture import (
    ApplicationCreate,
    ApplicationOut,
    DataSourceCreate,
    DataSourceOut,
    KPICreate,
    KPIOut,
    KPIUpdate,
    ProcessCreate,
    ProcessOut,
)
from app.schemas.opportunity import DependencyCreate, DependencyOut, DuplicatePair
from app.services import crossing
from app.services.audit import log_action, log_update, snapshot

router = APIRouter(prefix="/crossings", tags=["M6 - Croisements interservices"])


# ----------------------------------------------------------------------------- processus
@router.get("/processes", response_model=list[ProcessOut], summary="Lister les processus")
def list_processes(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.read")),
) -> list[Process]:
    return list(db.scalars(select(Process).where(Process.organization_id == tenant_id).order_by(Process.name)))


@router.post("/processes", response_model=ProcessOut, status_code=201, summary="Creer un processus")
def create_process(
    payload: ProcessCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.manage")),
) -> Process:
    process = Process(organization_id=tenant_id, **payload.model_dump())
    db.add(process)
    db.flush()
    log_action(
        db, action="create", entity_type="process", entity_id=process.id, entity_label=process.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(process),
    )
    return process


# --------------------------------------------------------------------------- applications
@router.get("/applications", response_model=list[ApplicationOut], summary="Lister les applications")
def list_applications(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.read")),
) -> list[Application]:
    return list(
        db.scalars(select(Application).where(Application.organization_id == tenant_id).order_by(Application.name))
    )


@router.post("/applications", response_model=ApplicationOut, status_code=201, summary="Creer une application")
def create_application(
    payload: ApplicationCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.manage")),
) -> Application:
    app_obj = Application(organization_id=tenant_id, **payload.model_dump())
    db.add(app_obj)
    db.flush()
    log_action(
        db, action="create", entity_type="application", entity_id=app_obj.id, entity_label=app_obj.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(app_obj),
    )
    return app_obj


# ----------------------------------------------------------------------- sources de donnees
@router.get("/datasources", response_model=list[DataSourceOut], summary="Lister les sources de donnees")
def list_datasources(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("data.read")),
) -> list[DataSource]:
    return list(
        db.scalars(select(DataSource).where(DataSource.organization_id == tenant_id).order_by(DataSource.name))
    )


@router.post("/datasources", response_model=DataSourceOut, status_code=201, summary="Creer une source de donnees")
def create_datasource(
    payload: DataSourceCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("data.manage")),
) -> DataSource:
    source = DataSource(organization_id=tenant_id, **payload.model_dump())
    db.add(source)
    db.flush()
    log_action(
        db, action="create", entity_type="datasource", entity_id=source.id, entity_label=source.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(source),
    )
    return source


# ----------------------------------------------------------------------------------- KPI
@router.get("/kpis", response_model=list[KPIOut], summary="Lister les KPI")
def list_kpis(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.read")),
    opportunity_id: int | None = None,
    department_id: int | None = None,
) -> list[KPI]:
    stmt = select(KPI).where(KPI.organization_id == tenant_id)
    if opportunity_id:
        stmt = stmt.where(KPI.opportunity_id == opportunity_id)
    if department_id:
        stmt = stmt.where(KPI.department_id == department_id)
    return list(db.scalars(stmt.order_by(KPI.name)))


@router.post("/kpis", response_model=KPIOut, status_code=201, summary="Creer un KPI")
def create_kpi(
    payload: KPICreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.manage")),
) -> KPI:
    kpi = KPI(organization_id=tenant_id, **payload.model_dump())
    db.add(kpi)
    db.flush()
    log_action(
        db, action="create", entity_type="kpi", entity_id=kpi.id, entity_label=kpi.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(kpi),
    )
    return kpi


@router.patch("/kpis/{kpi_id}", response_model=KPIOut, summary="Mettre a jour un KPI")
def update_kpi(
    kpi_id: int,
    payload: KPIUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("finance.manage")),
) -> KPI:
    kpi = get_or_404(db, KPI, kpi_id, tenant_id, "KPI")
    before = snapshot(kpi)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(kpi, key, value)
    db.flush()
    log_update(db, entity_type="kpi", instance=kpi, before=before, user=current_user)
    return kpi


# --------------------------------------------------------------------------- dependances
@router.get("/dependencies", response_model=list[DependencyOut], summary="Lister les dependances")
def list_dependencies(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.read")),
    opportunity_id: int | None = None,
) -> list[Dependency]:
    stmt = select(Dependency).where(Dependency.organization_id == tenant_id)
    if opportunity_id:
        stmt = stmt.where(
            (Dependency.source_opportunity_id == opportunity_id)
            | (Dependency.target_opportunity_id == opportunity_id)
        )
    return list(db.scalars(stmt))


@router.post("/dependencies", response_model=DependencyOut, status_code=201, summary="Declarer une dependance")
def create_dependency(
    payload: DependencyCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.manage")),
) -> Dependency:
    get_or_404(db, Opportunity, payload.source_opportunity_id, tenant_id, "Opportunite source")
    if payload.target_opportunity_id:
        get_or_404(db, Opportunity, payload.target_opportunity_id, tenant_id, "Opportunite cible")
    dep = Dependency(organization_id=tenant_id, **payload.model_dump())
    db.add(dep)
    db.flush()
    log_action(
        db, action="create", entity_type="dependency", entity_id=dep.id, entity_label=dep.label,
        organization_id=tenant_id, user=current_user, new_value=snapshot(dep),
    )
    return dep


@router.delete("/dependencies/{dependency_id}", status_code=204, response_model=None, summary="Supprimer une dependance")
def delete_dependency(
    dependency_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.manage")),
) -> None:
    dep = get_or_404(db, Dependency, dependency_id, tenant_id, "Dependance")
    log_action(
        db, action="delete", entity_type="dependency", entity_id=dep.id, entity_label=dep.label,
        organization_id=tenant_id, user=current_user, old_value=snapshot(dep),
    )
    db.delete(dep)


@router.get("/graph", summary="Graphe des dependances du portefeuille")
def graph(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.read")),
) -> dict:
    opportunities = list(db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique())
    dependencies = list(db.scalars(select(Dependency).where(Dependency.organization_id == tenant_id)))
    return crossing.dependency_graph(opportunities, dependencies)


@router.get(
    "/duplicates",
    response_model=list[DuplicatePair],
    summary="Detecter doublons et synergies entre opportunites",
)
def duplicates(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("architecture.read")),
    min_similarity: float = Query(default=0.30, ge=0, le=1),
) -> list[dict]:
    opportunities = list(db.scalars(select(Opportunity).where(Opportunity.organization_id == tenant_id)).unique())
    dependencies = list(db.scalars(select(Dependency).where(Dependency.organization_id == tenant_id)))
    return crossing.detect_duplicates(opportunities, dependencies, min_similarity=min_similarity)
