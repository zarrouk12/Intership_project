"""M1 - Authentification JWT et profil de l'utilisateur connecte."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select

from app.api.deps import ClientIp, CurrentUser, DbSession, Scope
from app.core.config import settings
from app.core.rbac import ALL_PERMISSIONS, ScopeLevel
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.rbac import Role, User, user_role
from app.schemas.auth import (
    DemoAccountsOut,
    LoginRequest,
    MeOut,
    PasswordChange,
    Token,
)
from app.schemas.common import Message
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["M1 - Authentification"])


def _authenticate(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contactez l'administrateur de votre organisation.",
        )
    return user


def _issue(db, user: User, ip: str | None) -> Token:
    token = create_access_token(
        subject=user.id,
        organization_id=user.organization_id,
        role=user.role_codes[0] if user.role_codes else None,
    )
    user.last_login_at = datetime.now(timezone.utc)
    log_action(
        db,
        action="login",
        entity_type="app_user",
        entity_id=user.id,
        entity_label=user.email,
        organization_id=user.organization_id,
        user=user,
        ip_address=ip,
    )
    return Token(access_token=token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/login", response_model=Token, summary="Connexion par email et mot de passe")
def login(payload: LoginRequest, db: DbSession, ip: ClientIp) -> Token:
    user = _authenticate(db, payload.email, payload.password)
    return _issue(db, user, ip)


@router.post("/token", response_model=Token, summary="Connexion compatible OAuth2 (form-data)")
def login_form(
    db: DbSession,
    ip: ClientIp,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = _authenticate(db, form.username, form.password)
    return _issue(db, user, ip)


def _role_summary(db, role: Role) -> dict:
    count = db.scalar(select(func.count()).select_from(user_role).where(user_role.c.role_id == role.id))
    return {
        "id": role.id,
        "code": role.code,
        "label": role.label,
        "description": role.description,
        "scope_level": role.scope_level,
        "is_system": role.is_system,
        "is_platform": role.is_platform,
        "permission_codes": role.permission_codes,
        "user_count": int(count or 0),
    }


@router.get(
    "/me",
    response_model=MeOut,
    summary="Profil complet : organisation, rattachements, rôles, permissions et périmètre",
)
def me(db: DbSession, current_user: CurrentUser, scope: Scope) -> dict:
    """Cet endpoint pilote toute l'interface.

    Le frontend n'invente jamais un droit : il n'affiche une entrée de menu ou un bouton
    que si la permission correspondante figure dans la liste renvoyee ici. Le backend
    revérifie de toute facon chaque appel.
    """
    organization = db.get(Organization, current_user.organization_id)
    roles = [_role_summary(db, role) for role in current_user.roles]

    # Role principal : celui dont le perimetre est le plus large, a defaut le premier.
    primary = None
    if roles:
        primary = min(roles, key=lambda r: ScopeLevel.rank(r["scope_level"]))

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "job_title": current_user.job_title,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "last_login_at": current_user.last_login_at,
        "organization": organization,
        "sites": current_user.sites,
        "departments": current_user.departments,
        "roles": roles,
        "primary_role": primary,
        # Le collaborateur Medicacom detient l'integralite du catalogue.
        "permissions": sorted(
            ALL_PERMISSIONS if current_user.is_superuser else current_user.permission_codes
        ),
        "scope": scope.as_dict(),
    }


@router.post("/password", response_model=Message, summary="Changer son propre mot de passe")
def change_password(
    payload: PasswordChange, db: DbSession, current_user: CurrentUser, ip: ClientIp
) -> Message:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    log_action(
        db,
        action="password_change",
        entity_type="app_user",
        entity_id=current_user.id,
        entity_label=current_user.email,
        organization_id=current_user.organization_id,
        user=current_user,
        ip_address=ip,
    )
    return Message(detail="Mot de passe mis à jour.")


@router.get(
    "/demo-accounts",
    response_model=DemoAccountsOut,
    summary="Comptes de demonstration (environnement de developpement uniquement)",
)
def demo_accounts(db: DbSession) -> dict:
    """Liste les comptes du jeu de demonstration, pour l'aide a la connexion.

    Cet endpoint n'existe qu'en developpement : en production il repond 404, comme une
    route inconnue. L'interface ne code donc aucun compte en dur, et la mise en
    production suffit a faire disparaitre l'aide, sans modification du frontend.

    Le mot de passe n'est renvoye que si l'exploitant l'a explicitement place dans
    DEMO_PASSWORD. Laisse vide, la liste reste informative et ne permet rien.
    """
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    users = db.scalars(
        select(User).where(User.is_active.is_(True)).order_by(User.full_name)
    ).unique()

    accounts = []
    for user in users:
        role = user.roles[0] if user.roles else None
        accounts.append(
            {
                "email": user.email,
                "full_name": user.full_name,
                "job_title": user.job_title,
                "role_label": role.label if role else "Aucun rôle",
                "scope_label": ScopeLevel.LABELS.get(user.scope_level, user.scope_level),
                "departments": [d.name for d in user.departments],
            }
        )

    # Les perimetres les plus larges d'abord : c'est l'ordre dans lequel on explore.
    accounts.sort(key=lambda a: (list(ScopeLevel.LABELS.values()).index(a["scope_label"]), a["full_name"]))

    return {"password": settings.DEMO_PASSWORD or None, "accounts": accounts}
