"""Schemas M1 : authentification, utilisateurs, roles, permissions, perimetre."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --------------------------------------------------------------------------- permissions
class PermissionOut(ORMModel):
    id: int
    code: str
    label: str
    module: str | None = None
    group: str | None = None


class RoleOut(ORMModel):
    id: int
    code: str
    label: str
    description: str | None = None
    scope_level: str
    is_system: bool
    is_platform: bool
    permissions: list[PermissionOut] = []


class RoleSummary(ORMModel):
    """Vue compacte d'un role, pour l'ecran d'administration."""

    id: int
    code: str
    label: str
    description: str | None = None
    scope_level: str
    is_system: bool
    is_platform: bool
    permission_codes: list[str] = []
    user_count: int = 0


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9_]+$")
    label: str
    description: str | None = None
    scope_level: str = "organization"
    permission_codes: list[str] = []


class RoleUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    scope_level: str | None = None
    permission_codes: list[str] | None = None


# ------------------------------------------------------------------------- utilisateurs
class OrganizationRef(ORMModel):
    id: int
    name: str
    code: str


class NamedRef(ORMModel):
    id: int
    name: str
    code: str


class UserOut(ORMModel):
    id: int
    organization_id: int
    department_id: int | None = None
    email: EmailStr
    full_name: str
    job_title: str | None = None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    roles: list[RoleOut] = []
    departments: list[NamedRef] = []
    sites: list[NamedRef] = []


class UserSummary(ORMModel):
    """Ligne de la table des utilisateurs dans l'administration."""

    id: int
    email: EmailStr
    full_name: str
    job_title: str | None = None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    role_codes: list[str] = []
    role_labels: list[str] = []
    department_names: list[str] = []
    site_names: list[str] = []
    scope_level: str


class ScopeOut(BaseModel):
    level: str
    level_label: str
    organization_id: int
    department_ids: list[int]
    site_ids: list[int]
    is_organization_wide: bool


class MeOut(BaseModel):
    """Profil complet renvoye apres connexion : pilote toute l'interface."""

    id: int
    email: EmailStr
    full_name: str
    job_title: str | None = None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    organization: OrganizationRef
    sites: list[NamedRef]
    departments: list[NamedRef]
    roles: list[RoleSummary]
    primary_role: RoleSummary | None = None
    permissions: list[str]
    scope: ScopeOut


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    job_title: str | None = None
    department_id: int | None = None
    department_ids: list[int] = []
    site_ids: list[int] = []
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    department_id: int | None = None
    department_ids: list[int] | None = None
    site_ids: list[int] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    role_codes: list[str] | None = None


class DemoAccount(BaseModel):
    """Compte de demonstration, propose a la connexion en developpement uniquement."""

    email: EmailStr
    full_name: str
    job_title: str | None = None
    role_label: str
    scope_label: str
    departments: list[str] = []


class DemoAccountsOut(BaseModel):
    """Le mot de passe n'est renvoye que si l'exploitant l'a explicitement publie."""

    password: str | None = None
    accounts: list[DemoAccount]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
