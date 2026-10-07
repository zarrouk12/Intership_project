"""M12 - Ecriture du journal d'audit immuable.

Le journal n'est jamais modifie ni supprime : seules des insertions sont autorisees.
Chaque entree conserve l'auteur, l'horodatage, l'entite visee et le couple
ancienne valeur / nouvelle valeur pour les champs reellement modifies.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.governance import AuditLog

IGNORED_FIELDS = {"created_at", "updated_at", "hashed_password"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def snapshot(obj: Any, fields: Iterable[str] | None = None) -> dict[str, Any]:
    """Photographie les colonnes d'une instance ORM."""
    if obj is None:
        return {}
    columns = [c.key for c in obj.__table__.columns]
    keys = [k for k in (fields or columns) if k in columns and k not in IGNORED_FIELDS]
    return {k: _jsonable(getattr(obj, k, None)) for k in keys}


def diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ne conserve que les champs dont la valeur a change."""
    old, new = {}, {}
    for key in set(before) | set(after):
        b, a = before.get(key), after.get(key)
        if b != a:
            old[key] = b
            new[key] = a
    return old, new


def log_action(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    entity_label: str | None = None,
    organization_id: int | None = None,
    user: Any | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        user_id=getattr(user, "id", None),
        user_email=getattr(user, "email", None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        old_value=_jsonable(old_value) if old_value else None,
        new_value=_jsonable(new_value) if new_value else None,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry


def log_update(
    db: Session,
    *,
    entity_type: str,
    instance: Any,
    before: dict[str, Any],
    user: Any | None = None,
    label: str | None = None,
) -> AuditLog | None:
    """Journalise une mise a jour en ne gardant que le delta reel."""
    after = snapshot(instance)
    old, new = diff(before, after)
    if not new:
        return None
    return log_action(
        db,
        action="update",
        entity_type=entity_type,
        entity_id=getattr(instance, "id", None),
        entity_label=label
        or getattr(instance, "title", None)
        or getattr(instance, "name", None)
        or getattr(instance, "code", None),
        organization_id=getattr(instance, "organization_id", None),
        user=user,
        old_value=old,
        new_value=new,
    )
