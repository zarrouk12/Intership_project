"""M8/M12 - Documents, versions, validations, notifications et journal d'audit."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, List

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ApprovalDecision, TimestampMixin


class Document(Base, TimestampMixin):
    """Fiche projet generee, note de cadrage, dossier de validation..."""

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(60), default="fiche_projet")
    status: Mapped[str] = mapped_column(String(40), default="brouillon")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    author: Mapped[str | None] = mapped_column(String(160))

    versions: Mapped[List["Version"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    approvals: Mapped[List["Approval"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class Version(Base, TimestampMixin):
    """Snapshot immuable du contenu d'un document."""

    __tablename__ = "version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str | None] = mapped_column(String(120))
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(160))

    document: Mapped[Document] = relationship(back_populates="versions")


class Approval(Base, TimestampMixin):
    """Decision de comite sur une fiche projet / une gate."""

    __tablename__ = "approval"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunity.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    stage_code: Mapped[str | None] = mapped_column(String(40))
    committee: Mapped[str | None] = mapped_column(String(160))
    approver_name: Mapped[str | None] = mapped_column(String(160))
    approver_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"))
    decision: Mapped[str] = mapped_column(String(40), default=ApprovalDecision.PENDING)
    decided_on: Mapped[date | None] = mapped_column(Date)
    comment: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document | None] = relationship(back_populates="approvals")


class Notification(Base, TimestampMixin):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(30), default="info")
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """M12 - Journal immuable : qui, quand, quoi, ancienne valeur -> nouvelle valeur."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    user_email: Mapped[str | None] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    entity_label: Mapped[str | None] = mapped_column(String(240))
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
