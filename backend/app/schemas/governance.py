"""Schemas M8 / M12 : documents, versions, validations, notifications, audit."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class VersionOut(ORMModel):
    id: int
    document_id: int
    number: int
    label: str | None = None
    content: dict[str, Any]
    change_summary: str | None = None
    created_by: str | None = None
    created_at: datetime


class ApprovalBase(BaseModel):
    document_id: int | None = None
    opportunity_id: int | None = None
    project_id: int | None = None
    stage_code: str | None = None
    committee: str | None = None
    approver_name: str | None = None
    decision: str = "en_attente"
    decided_on: date | None = None
    comment: str | None = None


class ApprovalCreate(ApprovalBase):
    pass


class ApprovalOut(ORMModel, ApprovalBase):
    id: int
    organization_id: int


class DocumentOut(ORMModel):
    id: int
    organization_id: int
    opportunity_id: int | None = None
    project_id: int | None = None
    code: str
    title: str
    doc_type: str
    status: str
    current_version: int
    author: str | None = None


class DocumentDetail(DocumentOut):
    versions: list[VersionOut] = []
    approvals: list[ApprovalOut] = []


class GenerateSheetRequest(BaseModel):
    change_summary: str | None = None
    label: str | None = None


class NotificationOut(ORMModel):
    id: int
    title: str
    body: str | None = None
    level: str
    entity_type: str | None = None
    entity_id: int | None = None
    is_read: bool
    created_at: datetime


class AuditLogOut(ORMModel):
    id: int
    organization_id: int | None = None
    user_id: int | None = None
    user_email: str | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    entity_label: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    created_at: datetime
