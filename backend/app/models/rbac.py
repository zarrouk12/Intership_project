"""M1 - Utilisateurs, roles et permissions (RBAC).

Un utilisateur porte un ou plusieurs roles ; chaque role porte un jeu de permissions et
un niveau de perimetre. Les rattachements aux sites et aux departements sont des
relations multiples : un responsable peut couvrir deux departements, un contributeur
peut intervenir sur deux sites.

`User.department_id` est conserve comme departement principal. Il alimente l'affichage
et sert de repli lorsque la table de rattachement est vide, ce qui garantit que les
donnees anterieures a la mise en place du perimetre restent exploitables.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.rbac import ScopeLevel, expand_legacy
from app.models.base import TimestampMixin

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
)

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)

user_department = Table(
    "user_department",
    Base.metadata,
    Column("user_id", ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", ForeignKey("department.id", ondelete="CASCADE"), primary_key=True),
)

user_site = Table(
    "user_site",
    Base.metadata,
    Column("user_id", ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True),
    Column("site_id", ForeignKey("site.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, TimestampMixin):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    module: Mapped[str | None] = mapped_column(String(40))
    #: Regroupement fonctionnel affiche dans l'ecran d'administration.
    group: Mapped[str | None] = mapped_column(String(60))

    roles: Mapped[List["Role"]] = relationship(secondary=role_permission, back_populates="permissions")


class Role(Base, TimestampMixin):
    __tablename__ = "role"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_role_org_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    #: Perimetre par defaut accorde par ce role.
    scope_level: Mapped[str] = mapped_column(
        String(30), default=ScopeLevel.ORGANIZATION, nullable=False
    )
    #: Role fourni par la plateforme : son jeu de permissions n'est pas modifiable par
    #: l'administrateur d'entreprise.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: Role reserve aux collaborateurs Medicacom, non attribuable dans un tenant client.
    is_platform: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permission, back_populates="roles", lazy="selectin"
    )
    users: Mapped[List["User"]] = relationship(secondary=user_role, back_populates="roles")

    @property
    def permission_codes(self) -> list[str]:
        return sorted(p.code for p in self.permissions)


class User(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Departement principal, conserve pour l'affichage et comme repli de perimetre.
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Collaborateur Medicacom : franchit la frontiere des organisations.
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[List[Role]] = relationship(
        secondary=user_role, back_populates="users", lazy="selectin"
    )
    departments: Mapped[List["Department"]] = relationship(  # noqa: F821
        secondary=user_department, lazy="selectin"
    )
    sites: Mapped[List["Site"]] = relationship(secondary=user_site, lazy="selectin")  # noqa: F821

    # ---------------------------------------------------------------- droits effectifs
    @property
    def permission_codes(self) -> set[str]:
        """Union des permissions portees par les roles de l'utilisateur.

        Les anciens codes eventuellement presents en base sont traduits vers le
        catalogue courant, afin qu'un role non migre reste fonctionnel.
        """
        raw = {p.code for role in self.roles for p in role.permissions}
        return expand_legacy(raw)

    @property
    def role_codes(self) -> list[str]:
        return [role.code for role in self.roles]

    @property
    def scope_level(self) -> str:
        """Perimetre effectif : le plus large parmi ceux des roles portes."""
        if self.is_superuser:
            return ScopeLevel.PLATFORM
        return ScopeLevel.widest(role.scope_level for role in self.roles)

    @property
    def department_ids(self) -> set[int]:
        """Departements de rattachement, avec repli sur le departement principal."""
        explicit = {d.id for d in self.departments}
        if explicit:
            return explicit
        return {self.department_id} if self.department_id else set()

    @property
    def site_ids(self) -> set[int]:
        return {s.id for s in self.sites}

    def has_permission(self, code: str) -> bool:
        if self.is_superuser:
            return True
        return code in self.permission_codes
