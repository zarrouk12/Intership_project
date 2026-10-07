"""RBAC dynamique : perimetres de role et rattachements multiples

Cette migration est ecrite pour s'appliquer sur une base deja peuplee :

  - les trois colonnes ajoutees a `role` sont creees avec une valeur par defaut serveur,
    afin que les lignes existantes soient renseignees sans violer la contrainte NOT NULL ;
    la valeur par defaut est ensuite retiree pour que ce soit l'application qui decide ;
  - les rattachements existants portes par `app_user.department_id` sont recopies dans la
    nouvelle table `user_department`, de sorte qu'aucun utilisateur ne perd son perimetre ;
  - `app_user.department_id` est conserve comme departement principal.

Revision ID: 0003_rbac_dynamique
Revises: d68675df2834
Create Date: 2026-09-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_rbac_dynamique"
down_revision: Union[str, None] = "d68675df2834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- rattachements multiples -----------------------------------------------------
    op.create_table(
        "user_department",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["department.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "department_id"),
    )
    op.create_table(
        "user_site",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["site.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "site_id"),
    )

    # --- traçabilite des connexions --------------------------------------------------
    op.add_column("app_user", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # --- catalogue de permissions enrichi --------------------------------------------
    op.add_column("permission", sa.Column("group", sa.String(length=60), nullable=True))
    op.alter_column(
        "permission",
        "label",
        existing_type=sa.VARCHAR(length=160),
        type_=sa.String(length=200),
        existing_nullable=False,
    )

    # --- perimetre et nature des roles ------------------------------------------------
    # La valeur par defaut serveur renseigne les lignes deja presentes, puis disparait.
    op.add_column(
        "role",
        sa.Column("scope_level", sa.String(length=30), nullable=False, server_default="organization"),
    )
    op.add_column(
        "role",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "role",
        sa.Column("is_platform", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("role", "scope_level", server_default=None)
    op.alter_column("role", "is_system", server_default=None)
    op.alter_column("role", "is_platform", server_default=None)

    # --- reprise des rattachements existants -------------------------------------------
    op.execute(
        """
        INSERT INTO user_department (user_id, department_id)
        SELECT id, department_id
        FROM app_user
        WHERE department_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Un utilisateur herite du site de son departement principal, lorsqu'il en a un.
    op.execute(
        """
        INSERT INTO user_site (user_id, site_id)
        SELECT u.id, d.site_id
        FROM app_user u
        JOIN department d ON d.id = u.department_id
        WHERE d.site_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("role", "is_platform")
    op.drop_column("role", "is_system")
    op.drop_column("role", "scope_level")
    op.alter_column(
        "permission",
        "label",
        existing_type=sa.String(length=200),
        type_=sa.VARCHAR(length=160),
        existing_nullable=False,
    )
    op.drop_column("permission", "group")
    op.drop_column("app_user", "last_login_at")
    op.drop_table("user_site")
    op.drop_table("user_department")
