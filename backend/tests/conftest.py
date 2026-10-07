"""Fixtures des tests d'autorisation.

Les tests s'executent contre la base de developpement peuplee par `python -m app.seed`.
Ils n'ecrivent que dans une organisation temporaire creee puis supprimee par la fixture
`other_organization`, et nettoient chaque objet qu'ils creent dans l'organisation de
demonstration. Aucune donnee du jeu de demonstration n'est alteree.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.core.rbac import ROLE_BY_CODE
from app.core.security import hash_password
from app.main import app
from app.models.organization import Department, Organization, Site
from app.models.rbac import Permission, Role, User

API = "/api/v1"
PASSWORD = "medicacom2026"

#: Un compte de demonstration par role fonctionnel teste.
ACCOUNTS: dict[str, str] = {
    "direction": "marwen.b@medicacom.com",
    "admin_entreprise": "admin.entreprise@medicacom.com",
    "resp_commercial": "l.trabelsi@medicacom.com",
    "resp_production": "h.gharbi@medicacom.com",
    "contributeur": "a.rousseau@medicacom.com",
    "dsi": "k.zouari@medicacom.com",
    "data_office": "n.hamdi@medicacom.com",
    "ai_lead": "y.benali@medicacom.com",
    "finance": "m.dupuis@medicacom.com",
    "pmo": "f.moreau@medicacom.com",
    "auditeur": "audit@medicacom.com",
    "plateforme": "admin@medicacom.com",
}


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _login(client: TestClient, email: str) -> str:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, f"Connexion impossible pour {email} : {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def tokens(client: TestClient) -> dict[str, str]:
    """Un jeton par role, emis une seule fois pour toute la session de test."""
    return {name: _login(client, email) for name, email in ACCOUNTS.items()}


@pytest.fixture
def auth(tokens):
    """Fabrique d'en-tetes : `auth("finance")` renvoie l'en-tete Authorization."""

    def _headers(role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens[role]}"}

    return _headers


@pytest.fixture(scope="session")
def demo_org(db) -> Organization:
    org = db.scalar(select(Organization).where(Organization.code == "MEDICACOM"))
    assert org is not None, "Lancez `python -m app.seed` avant d'exécuter les tests."
    return org


@pytest.fixture(scope="session")
def departments(db, demo_org) -> dict[str, Department]:
    rows = db.scalars(select(Department).where(Department.organization_id == demo_org.id))
    return {d.code: d for d in rows}


@pytest.fixture(scope="session")
def other_organization(db):
    """Seconde organisation, avec son propre utilisateur, pour tester l'isolation.

    Elle est entierement supprimee a la fin de la session : la base de developpement
    retrouve son etat initial.
    """
    org = Organization(name="Pharma Test SA", code="PHARMATEST", industry="Pharmaceutique")
    db.add(org)
    db.flush()

    site = Site(organization_id=org.id, name="Site de test", code="TST")
    db.add(site)
    db.flush()
    department = Department(organization_id=org.id, name="Département de test", code="TSTD", site_id=site.id)
    db.add(department)
    db.flush()

    # L'utilisateur de test cumule l'administration et le pilotage des opportunites.
    # Sans la permission d'ecriture, une tentative inter-tenant serait refusee par le
    # controle de permission (403) et le test ne prouverait rien sur l'isolation.
    roles = []
    for code in ("admin_entreprise", "responsable_departement"):
        template = ROLE_BY_CODE[code]
        permissions = list(
            db.scalars(select(Permission).where(Permission.code.in_(template.permissions)))
        )
        role = Role(
            organization_id=org.id,
            code=template.code,
            label=template.label,
            scope_level=template.scope_level,
            is_system=True,
        )
        role.permissions = permissions
        db.add(role)
        roles.append(role)
    db.flush()

    user = User(
        organization_id=org.id,
        email="admin@pharmatest-demo.com",
        full_name="Administrateur Pharma Test",
        hashed_password=hash_password(PASSWORD),
        department_id=department.id,
    )
    user.roles = roles
    user.departments = [department]
    db.add(user)
    db.commit()

    yield {"organization": org, "user": user, "department": department, "site": site}

    # Nettoyage complet
    user.roles = []
    user.departments = []
    user.sites = []
    db.flush()
    db.execute(delete(User).where(User.organization_id == org.id))
    db.execute(delete(Role).where(Role.organization_id == org.id))
    db.execute(delete(Department).where(Department.organization_id == org.id))
    db.execute(delete(Site).where(Site.organization_id == org.id))
    db.execute(delete(Organization).where(Organization.id == org.id))
    db.commit()


@pytest.fixture
def other_token(client, other_organization) -> str:
    return _login(client, "admin@pharmatest-demo.com")


@pytest.fixture
def cleanup(db):
    """Enregistre les objets crees par un test pour les supprimer a la fin."""
    created: list[tuple] = []

    def _register(model, obj_id: int) -> None:
        created.append((model, obj_id))

    yield _register

    for model, obj_id in reversed(created):
        obj = db.get(model, obj_id)
        if obj is not None:
            if hasattr(obj, "roles"):
                obj.roles = []
            if hasattr(obj, "departments"):
                obj.departments = []
            if hasattr(obj, "sites"):
                obj.sites = []
            db.delete(obj)
    db.commit()
