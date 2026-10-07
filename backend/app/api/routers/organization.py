"""M1 - Organisation, sites, departements, utilisateurs, roles et permissions.

Chaque endpoint porte sa propre verification de permission. Les endpoints de lecture ne
font pas exception : sans `user.read`, un utilisateur ne voit pas l'annuaire de son
organisation, meme s'il est authentifie.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import (
    ClientIp,
    CurrentUser,
    DbSession,
    Scope,
    TenantId,
    get_or_404,
    require_permission,
)
from app.core.rbac import (
    ALL_PERMISSIONS,
    PLATFORM_ONLY,
    ROLE_BY_CODE,
    ScopeLevel,
)
from app.core.security import hash_password
from app.models.organization import Department, Organization, Site
from app.models.rbac import Permission, Role, User, user_role
from app.schemas.auth import (
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleSummary,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserSummary,
    UserUpdate,
)
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    OrganizationOut,
    OrganizationUpdate,
    SiteCreate,
    SiteOut,
    SiteUpdate,
)
from app.services.audit import log_action, log_update, snapshot

router = APIRouter(prefix="/org", tags=["M1 - Organisation & RBAC"])


# ======================================================================================
# Organisation
# ======================================================================================

@router.get("/organization", response_model=OrganizationOut, summary="Organisation courante")
def read_organization(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("organization.read")),
) -> Organization:
    org = db.get(Organization, tenant_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation introuvable")
    return org


@router.patch("/organization", response_model=OrganizationOut, summary="Modifier l'organisation")
def update_organization(
    payload: OrganizationUpdate,
    db: DbSession,
    tenant_id: TenantId,
    ip: ClientIp,
    current_user: User = Depends(require_permission("organization.manage")),
) -> Organization:
    org = db.get(Organization, tenant_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation introuvable")
    before = snapshot(org)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, key, value)
    db.flush()
    log_update(db, entity_type="organization", instance=org, before=before, user=current_user)
    return org


# ======================================================================================
# Sites
# ======================================================================================

@router.get("/sites", response_model=list[SiteOut], summary="Lister les sites")
def list_sites(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("site.read")),
) -> list[Site]:
    return list(db.scalars(select(Site).where(Site.organization_id == tenant_id).order_by(Site.name)))


@router.post("/sites", response_model=SiteOut, status_code=201, summary="Créer un site")
def create_site(
    payload: SiteCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("site.manage")),
) -> Site:
    site = Site(organization_id=tenant_id, **payload.model_dump())
    db.add(site)
    db.flush()
    log_action(
        db, action="create", entity_type="site", entity_id=site.id, entity_label=site.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(site),
    )
    return site


@router.patch("/sites/{site_id}", response_model=SiteOut, summary="Modifier un site")
def update_site(
    site_id: int,
    payload: SiteUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("site.manage")),
) -> Site:
    site = get_or_404(db, Site, site_id, tenant_id, "Site")
    before = snapshot(site)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(site, key, value)
    db.flush()
    log_update(db, entity_type="site", instance=site, before=before, user=current_user)
    return site


# ======================================================================================
# Departements
# ======================================================================================

@router.get("/departments", response_model=list[DepartmentOut], summary="Lister les départements")
def list_departments(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("department.read")),
) -> list[Department]:
    return list(
        db.scalars(
            select(Department).where(Department.organization_id == tenant_id).order_by(Department.name)
        )
    )


@router.post("/departments", response_model=DepartmentOut, status_code=201, summary="Créer un département")
def create_department(
    payload: DepartmentCreate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("department.manage")),
) -> Department:
    dept = Department(organization_id=tenant_id, **payload.model_dump())
    db.add(dept)
    db.flush()
    log_action(
        db, action="create", entity_type="department", entity_id=dept.id, entity_label=dept.name,
        organization_id=tenant_id, user=current_user, new_value=snapshot(dept),
    )
    return dept


@router.patch("/departments/{dept_id}", response_model=DepartmentOut, summary="Modifier un département")
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("department.manage")),
) -> Department:
    dept = get_or_404(db, Department, dept_id, tenant_id, "Département")
    before = snapshot(dept)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)
    db.flush()
    log_update(db, entity_type="department", instance=dept, before=before, user=current_user)
    return dept


# ======================================================================================
# Utilisateurs
# ======================================================================================

def _assignable_roles(db, tenant_id: int, codes: list[str], actor: User) -> list[Role]:
    """Resout des codes de role en objets, en refusant tout role hors du tenant.

    Un role de plateforme n'est attribuable que par un collaborateur Medicacom : sans
    cette barriere, un administrateur d'entreprise pourrait s'octroyer un acces
    inter-organisations en s'attribuant le role `admin_medicacom`.
    """
    if not codes:
        return []
    roles = list(
        db.scalars(select(Role).where(Role.organization_id == tenant_id, Role.code.in_(codes)))
    )
    found = {role.code for role in roles}
    unknown = [code for code in codes if code not in found]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rôle inconnu dans cette organisation : {', '.join(unknown)}",
        )
    if not actor.is_superuser:
        forbidden = [role.code for role in roles if role.is_platform]
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Le rôle {', '.join(forbidden)} est réservé à l'administration "
                    "de la plateforme Medicacom."
                ),
            )
    return roles


def _resolve_scope_entities(db, tenant_id: int, department_ids: list[int], site_ids: list[int]):
    """Verifie que les rattachements demandes appartiennent bien au tenant."""
    departments = []
    if department_ids:
        departments = list(
            db.scalars(
                select(Department).where(
                    Department.organization_id == tenant_id, Department.id.in_(department_ids)
                )
            )
        )
        if len(departments) != len(set(department_ids)):
            raise HTTPException(status_code=404, detail="Département introuvable dans cette organisation")
    sites = []
    if site_ids:
        sites = list(
            db.scalars(select(Site).where(Site.organization_id == tenant_id, Site.id.in_(site_ids)))
        )
        if len(sites) != len(set(site_ids)):
            raise HTTPException(status_code=404, detail="Site introuvable dans cette organisation")
    return departments, sites


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "job_title": user.job_title,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "last_login_at": user.last_login_at,
        "role_codes": user.role_codes,
        "role_labels": [role.label for role in user.roles],
        "department_names": [d.name for d in user.departments],
        "site_names": [s.name for s in user.sites],
        "scope_level": user.scope_level,
    }


@router.get("/users", response_model=list[UserSummary], summary="Lister les utilisateurs")
def list_users(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("user.read")),
) -> list[dict]:
    users = db.scalars(
        select(User).where(User.organization_id == tenant_id).order_by(User.full_name)
    ).unique()
    return [_user_summary(user) for user in users]


@router.get("/users/{user_id}", response_model=UserOut, summary="Détail d'un utilisateur")
def read_user(
    user_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("user.read")),
) -> User:
    return get_or_404(db, User, user_id, tenant_id, "Utilisateur")


@router.post("/users", response_model=UserOut, status_code=201, summary="Créer un utilisateur")
def create_user(
    payload: UserCreate,
    db: DbSession,
    tenant_id: TenantId,
    ip: ClientIp,
    current_user: User = Depends(require_permission("user.create")),
) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    departments, sites = _resolve_scope_entities(
        db, tenant_id, payload.department_ids, payload.site_ids
    )
    if payload.department_id:
        get_or_404(db, Department, payload.department_id, tenant_id, "Département")

    user = User(
        organization_id=tenant_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        job_title=payload.job_title,
        department_id=payload.department_id,
        hashed_password=hash_password(payload.password),
    )
    user.roles = _assignable_roles(db, tenant_id, payload.role_codes, current_user)
    user.departments = departments
    user.sites = sites
    db.add(user)
    db.flush()

    log_action(
        db, action="create", entity_type="app_user", entity_id=user.id, entity_label=user.email,
        organization_id=tenant_id, user=current_user, ip_address=ip,
        new_value={
            **snapshot(user),
            "roles": user.role_codes,
            "departments": [d.name for d in user.departments],
            "sites": [s.name for s in user.sites],
        },
    )
    return user


@router.patch("/users/{user_id}", response_model=UserOut, summary="Modifier un utilisateur")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    tenant_id: TenantId,
    ip: ClientIp,
    current_user: User = Depends(require_permission("user.update")),
) -> User:
    user = get_or_404(db, User, user_id, tenant_id, "Utilisateur")
    before = {
        **snapshot(user),
        "roles": user.role_codes,
        "departments": [d.name for d in user.departments],
        "sites": [s.name for s in user.sites],
    }

    data = payload.model_dump(exclude_unset=True)
    role_codes = data.pop("role_codes", None)
    department_ids = data.pop("department_ids", None)
    site_ids = data.pop("site_ids", None)
    password = data.pop("password", None)
    is_active = data.pop("is_active", None)

    if is_active is not None:
        if not current_user.has_permission("user.disable"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : activer ou désactiver un compte requiert user.disable.",
            )
        if user.id == current_user.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vous ne pouvez pas désactiver votre propre compte.",
            )
        user.is_active = is_active

    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.hashed_password = hash_password(password)
    if role_codes is not None:
        user.roles = _assignable_roles(db, tenant_id, role_codes, current_user)
    if department_ids is not None or site_ids is not None:
        departments, sites = _resolve_scope_entities(
            db, tenant_id, department_ids or [], site_ids or []
        )
        if department_ids is not None:
            user.departments = departments
        if site_ids is not None:
            user.sites = sites
    db.flush()

    after = {
        **snapshot(user),
        "roles": user.role_codes,
        "departments": [d.name for d in user.departments],
        "sites": [s.name for s in user.sites],
    }
    changed_old = {k: v for k, v in before.items() if after.get(k) != v}
    changed_new = {k: v for k, v in after.items() if before.get(k) != v}
    if changed_new:
        log_action(
            db, action="update", entity_type="app_user", entity_id=user.id,
            entity_label=user.email, organization_id=tenant_id, user=current_user,
            ip_address=ip, old_value=changed_old, new_value=changed_new,
        )
    return user


# ======================================================================================
# Roles et permissions
# ======================================================================================

@router.get("/roles", response_model=list[RoleSummary], summary="Lister les rôles")
def list_roles(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("role.read")),
) -> list[dict]:
    roles = list(db.scalars(select(Role).where(Role.organization_id == tenant_id).order_by(Role.label)))
    counts = dict(
        db.execute(
            select(user_role.c.role_id, func.count(user_role.c.user_id)).group_by(user_role.c.role_id)
        ).all()
    )
    return [
        {
            "id": role.id,
            "code": role.code,
            "label": role.label,
            "description": role.description,
            "scope_level": role.scope_level,
            "is_system": role.is_system,
            "is_platform": role.is_platform,
            "permission_codes": role.permission_codes,
            "user_count": int(counts.get(role.id, 0)),
        }
        for role in roles
    ]


def _assignable_permissions(db, codes: list[str], actor: User) -> list[Permission]:
    """Resout des codes de permission, en interdisant les permissions de plateforme."""
    unknown = [code for code in codes if code not in ALL_PERMISSIONS]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Permission inconnue : {', '.join(unknown)}",
        )
    if not actor.is_superuser:
        reserved = [code for code in codes if code in PLATFORM_ONLY]
        if reserved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission réservée à la plateforme : {', '.join(reserved)}. "
                    "Elle ne peut pas être accordée depuis un tenant client."
                ),
            )
    return list(db.scalars(select(Permission).where(Permission.code.in_(codes))))


@router.post("/roles", response_model=RoleSummary, status_code=201, summary="Créer un rôle")
def create_role(
    payload: RoleCreate,
    db: DbSession,
    tenant_id: TenantId,
    ip: ClientIp,
    current_user: User = Depends(require_permission("role.manage")),
) -> dict:
    if payload.scope_level not in ScopeLevel.ORDER:
        raise HTTPException(status_code=422, detail="Niveau de périmètre inconnu")
    if payload.scope_level == ScopeLevel.PLATFORM and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le périmètre plateforme est réservé à l'administration Medicacom.",
        )
    if db.scalar(select(Role).where(Role.organization_id == tenant_id, Role.code == payload.code)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce code de rôle existe déjà")

    role = Role(
        organization_id=tenant_id,
        code=payload.code,
        label=payload.label,
        description=payload.description,
        scope_level=payload.scope_level,
        is_system=False,
        is_platform=False,
    )
    role.permissions = _assignable_permissions(db, payload.permission_codes, current_user)
    db.add(role)
    db.flush()
    log_action(
        db, action="create", entity_type="role", entity_id=role.id, entity_label=role.code,
        organization_id=tenant_id, user=current_user, ip_address=ip,
        new_value={"code": role.code, "scope_level": role.scope_level,
                   "permissions": role.permission_codes},
    )
    return {**{c.key: getattr(role, c.key) for c in role.__table__.columns},
            "permission_codes": role.permission_codes, "user_count": 0}


@router.patch("/roles/{role_id}", response_model=RoleSummary, summary="Modifier un rôle")
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: DbSession,
    tenant_id: TenantId,
    ip: ClientIp,
    current_user: User = Depends(require_permission("role.manage")),
) -> dict:
    role = get_or_404(db, Role, role_id, tenant_id, "Rôle")
    if role.is_system and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Le rôle « {role.label} » est fourni par la plateforme et n'est pas modifiable. "
                "Créez un rôle personnalisé pour ajuster les droits."
            ),
        )

    before = {"label": role.label, "scope_level": role.scope_level,
              "permissions": role.permission_codes}
    data = payload.model_dump(exclude_unset=True)
    permission_codes = data.pop("permission_codes", None)
    scope_level = data.get("scope_level")
    if scope_level and scope_level not in ScopeLevel.ORDER:
        raise HTTPException(status_code=422, detail="Niveau de périmètre inconnu")
    if scope_level == ScopeLevel.PLATFORM and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le périmètre plateforme est réservé à l'administration Medicacom.",
        )
    for key, value in data.items():
        setattr(role, key, value)
    if permission_codes is not None:
        role.permissions = _assignable_permissions(db, permission_codes, current_user)
    db.flush()

    after = {"label": role.label, "scope_level": role.scope_level,
             "permissions": role.permission_codes}
    if after != before:
        log_action(
            db, action="update", entity_type="role", entity_id=role.id, entity_label=role.code,
            organization_id=tenant_id, user=current_user, ip_address=ip,
            old_value=before, new_value=after,
        )
    count = db.scalar(select(func.count()).select_from(user_role).where(user_role.c.role_id == role.id))
    return {**{c.key: getattr(role, c.key) for c in role.__table__.columns},
            "permission_codes": role.permission_codes, "user_count": int(count or 0)}


@router.get("/permissions", response_model=list[PermissionOut], summary="Catalogue des permissions")
def list_permissions(
    db: DbSession,
    current_user: User = Depends(require_permission("role.read")),
) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.module, Permission.code)))


@router.get("/role-templates", summary="Modèles de rôles fournis par la plateforme")
def role_templates(current_user: User = Depends(require_permission("role.read"))) -> list[dict]:
    return [
        {
            "code": template.code,
            "label": template.label,
            "description": template.description,
            "scope_level": template.scope_level,
            "scope_label": ScopeLevel.LABELS[template.scope_level],
            "is_platform": template.is_platform,
            "permissions": list(template.permissions),
        }
        for template in ROLE_BY_CODE.values()
    ]


@router.get("/scope", summary="Périmètre effectif de l'utilisateur connecté")
def my_scope(scope: Scope, current_user: CurrentUser) -> dict:
    return {
        **scope.as_dict(),
        "roles": current_user.role_codes,
        "permissions": sorted(current_user.permission_codes),
    }
