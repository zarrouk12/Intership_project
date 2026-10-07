"""M12 - Administration : journal d'audit immuable et notifications."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.models.rbac import User
from app.api.deps import CurrentUser, DbSession, TenantId, get_or_404, require_permission
from app.models.governance import AuditLog, Notification
from app.schemas.governance import AuditLogOut, NotificationOut

router = APIRouter(prefix="/admin", tags=["M12 - Administration & audit"])


@router.get(
    "/audit-logs",
    response_model=list[AuditLogOut],
    summary="Consulter le journal d'audit (lecture seule, aucune modification possible)",
)
def list_audit_logs(
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("audit.read")),
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    user_id: int | None = None,
    since: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.organization_id == tenant_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.get("/audit-logs/{entity_type}/{entity_id}", response_model=list[AuditLogOut], summary="Historique d'une entite")
def entity_history(
    entity_type: str,
    entity_id: int,
    db: DbSession,
    tenant_id: TenantId,
    current_user: User = Depends(require_permission("audit.read")),
) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.organization_id == tenant_id,
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        )
        .order_by(AuditLog.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/notifications", response_model=list[NotificationOut], summary="Notifications de l'utilisateur")
def list_notifications(
    db: DbSession,
    tenant_id: TenantId,
    current_user: CurrentUser,
    unread_only: bool = False,
) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.organization_id == tenant_id,
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(db.scalars(stmt.order_by(Notification.created_at.desc()).limit(50)))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut, summary="Marquer comme lue")
def mark_read(
    notification_id: int, db: DbSession, tenant_id: TenantId, current_user: CurrentUser
) -> Notification:
    notification = get_or_404(db, Notification, notification_id, tenant_id, "Notification")
    notification.is_read = True
    db.flush()
    return notification
