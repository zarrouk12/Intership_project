"""Dependances communes : session, utilisateur courant, RBAC, perimetre, multi-tenant.

Toute decision d'autorisation passe par ce module. Une regle et une seule :

    permission (ce qui est autorise)  x  perimetre (sur quoi)

Aucun endpoint ne teste un nom de role. Masquer un bouton cote React ne protege rien :
chaque endpoint sensible porte sa propre verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac import ScopeLevel
from app.core.security import decode_access_token
from app.models.rbac import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


# ======================================================================================
# Utilisateur courant
# ======================================================================================

def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise credentials_error

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contactez l'administrateur de votre organisation.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_tenant_id(current_user: CurrentUser) -> int:
    """Organisation imposee par le jeton : aucune requete ne peut en sortir."""
    return current_user.organization_id


TenantId = Annotated[int, Depends(get_tenant_id)]


# ======================================================================================
# Perimetre effectif
# ======================================================================================

@dataclass
class AccessScope:
    """Perimetre effectif de l'utilisateur, calcule une fois par requete."""

    user: User
    organization_id: int
    level: str
    department_ids: set[int]
    site_ids: set[int]

    # ------------------------------------------------------------------ interrogation
    @property
    def is_platform(self) -> bool:
        return self.level == ScopeLevel.PLATFORM

    @property
    def is_organization_wide(self) -> bool:
        """Vrai lorsque l'utilisateur voit et modifie toute son organisation."""
        return self.level in (ScopeLevel.PLATFORM, ScopeLevel.ORGANIZATION)

    def visible_departments(self) -> set[int] | None:
        """Departements lisibles. `None` signifie : aucune restriction."""
        if self.is_organization_wide:
            return None
        return set(self.department_ids)

    def can_read_department(self, department_id: int | None) -> bool:
        if self.is_organization_wide:
            return True
        if department_id is None:
            # Un objet non rattache reste lisible : il n'appartient a aucun departement
            # concurrent et masquer l'existence d'un orphelin n'apporte rien.
            return True
        return department_id in self.department_ids

    def can_write_department(self, department_id: int | None) -> bool:
        """L'ecriture ne deborde jamais du perimetre, meme quand la lecture le permet."""
        if self.is_organization_wide:
            return True
        if department_id is None:
            return False
        return department_id in self.department_ids

    def has(self, *codes: str) -> bool:
        return all(self.user.has_permission(code) for code in codes)

    def has_any(self, *codes: str) -> bool:
        return any(self.user.has_permission(code) for code in codes)

    # ------------------------------------------------------------------- application
    def assert_can_write_department(self, department_id: int | None, label: str = "cet élément") -> None:
        if not self.can_write_department(department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Périmètre insuffisant pour modifier {label} : "
                    f"votre accès est limité à vos départements de rattachement."
                ),
            )

    def filter_by_department(self, stmt, column):
        """Restreint une requete aux departements du perimetre, le cas echeant."""
        allowed = self.visible_departments()
        if allowed is None:
            return stmt
        if not allowed:
            # Perimetre departemental sans rattachement : rien n'est visible.
            return stmt.where(column.is_(None), column.is_not(None))
        return stmt.where(column.in_(allowed))

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "level_label": ScopeLevel.LABELS.get(self.level, self.level),
            "organization_id": self.organization_id,
            "department_ids": sorted(self.department_ids),
            "site_ids": sorted(self.site_ids),
            "is_organization_wide": self.is_organization_wide,
        }


def get_scope(current_user: CurrentUser) -> AccessScope:
    return AccessScope(
        user=current_user,
        organization_id=current_user.organization_id,
        level=current_user.scope_level,
        department_ids=current_user.department_ids,
        site_ids=current_user.site_ids,
    )


Scope = Annotated[AccessScope, Depends(get_scope)]


# ======================================================================================
# Controle de permissions
# ======================================================================================

def _deny(missing: Iterable[str], mode: str = "toutes") -> HTTPException:
    codes = ", ".join(sorted(missing))
    article = "les permissions" if mode == "toutes" else "l'une des permissions"
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Accès refusé : cette action requiert {article} suivantes — {codes}.",
    )


def require_permission(*codes: str) -> Callable[[User], User]:
    """Exige **toutes** les permissions listees.

    Renvoie une dependance FastAPI a poser en `Depends(...)` sur l'endpoint. Le
    superutilisateur de plateforme franchit tous les controles de permission, mais reste
    soumis au filtrage multi-tenant de `get_or_404`.
    """

    def _checker(current_user: CurrentUser) -> User:
        if current_user.is_superuser:
            return current_user
        owned = current_user.permission_codes
        missing = [code for code in codes if code not in owned]
        if missing:
            raise _deny(missing)
        return current_user

    return _checker


def require_any_permission(*codes: str) -> Callable[[User], User]:
    """Exige **au moins une** des permissions listees."""

    def _checker(current_user: CurrentUser) -> User:
        if current_user.is_superuser:
            return current_user
        owned = current_user.permission_codes
        if not any(code in owned for code in codes):
            raise _deny(codes, mode="une")
        return current_user

    return _checker


#: Conserve pour compatibilite : `require_permissions` etait le nom historique.
require_permissions = require_permission


def require_platform_admin(current_user: CurrentUser) -> User:
    """Reserve aux collaborateurs Medicacom administrant la plateforme."""
    if current_user.is_superuser or current_user.has_permission("platform.admin"):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès réservé à l'administration de la plateforme Medicacom.",
    )


PlatformAdmin = Annotated[User, Depends(require_platform_admin)]


# ======================================================================================
# Divers
# ======================================================================================

def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(client_ip)]


def tenant_filter(model, tenant_id: int):
    """Applique systematiquement le filtre organization_id sur une requete."""
    return select(model).where(model.organization_id == tenant_id)


def get_or_404(db: Session, model, obj_id: int, tenant_id: int, label: str = "Ressource"):
    """Recupere une entite en verifiant son appartenance au tenant courant.

    Une ressource d'une autre organisation repond 404 et non 403 : le code 403
    confirmerait son existence a un utilisateur qui n'a pas a la connaitre.
    """
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "organization_id", None) != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} introuvable")
    return obj


def get_scoped_or_404(
    db: Session, model, obj_id: int, scope: AccessScope, label: str = "Ressource", *, write: bool = False
):
    """Comme `get_or_404`, en verifiant en plus le perimetre departemental.

    En lecture, un objet hors perimetre repond 404. En ecriture, un objet lisible mais
    hors perimetre d'ecriture repond 403 : l'utilisateur sait qu'il existe, on lui dit
    seulement qu'il ne peut pas le modifier.
    """
    obj = get_or_404(db, model, obj_id, scope.organization_id, label)
    department_id = getattr(obj, "department_id", None)
    if write:
        scope.assert_can_write_department(department_id, label.lower())
    elif not scope.can_read_department(department_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} introuvable")
    return obj
