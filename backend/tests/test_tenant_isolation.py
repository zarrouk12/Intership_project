"""Isolation multi-tenant : une organisation ne voit jamais les donnees d'une autre.

Le point sensible est la manipulation d'identifiants dans l'URL : connaitre l'identifiant
d'une ressource d'un autre tenant ne doit donner aucun acces.
"""
from __future__ import annotations

import pytest

from tests.conftest import API


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_chaque_organisation_ne_voit_que_la_sienne(client, auth, other_token):
    medicacom = client.get(f"{API}/org/organization", headers=auth("admin_entreprise")).json()
    pharmatest = client.get(f"{API}/org/organization", headers=_headers(other_token)).json()

    assert medicacom["code"] == "MEDICACOM"
    assert pharmatest["code"] == "PHARMATEST"
    assert medicacom["id"] != pharmatest["id"]


def test_les_annuaires_ne_se_recouvrent_pas(client, auth, other_token):
    medicacom = client.get(f"{API}/org/users", headers=auth("admin_entreprise")).json()
    pharmatest = client.get(f"{API}/org/users", headers=_headers(other_token)).json()

    emails_medicacom = {u["email"] for u in medicacom}
    emails_pharmatest = {u["email"] for u in pharmatest}
    assert not emails_medicacom & emails_pharmatest
    assert emails_pharmatest == {"admin@pharmatest-demo.com"}


def test_un_tenant_ne_lit_pas_l_utilisateur_d_un_autre(client, auth, other_token, db, demo_org):
    from sqlalchemy import select

    from app.models.rbac import User

    cible = db.scalar(select(User).where(User.email == "m.dupuis@medicacom.com"))
    response = client.get(f"{API}/org/users/{cible.id}", headers=_headers(other_token))
    assert response.status_code == 404, "L'utilisateur d'un autre tenant doit être introuvable"


def test_un_tenant_ne_lit_pas_l_opportunite_d_un_autre(client, auth, other_token):
    opportunites = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    cible = opportunites[0]["id"]

    response = client.get(f"{API}/opportunities/{cible}", headers=_headers(other_token))
    assert response.status_code == 404


def test_un_tenant_ne_modifie_pas_l_opportunite_d_un_autre(client, auth, other_token):
    opportunites = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    cible = opportunites[0]["id"]

    response = client.patch(
        f"{API}/opportunities/{cible}",
        json={"summary": "modification inter-tenant"},
        headers=_headers(other_token),
    )
    assert response.status_code == 404


def test_un_tenant_ne_supprime_pas_l_opportunite_d_un_autre(client, auth, other_token):
    opportunites = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    cible = opportunites[-1]["id"]

    response = client.delete(f"{API}/opportunities/{cible}", headers=_headers(other_token))
    assert response.status_code == 404

    # La ressource est toujours la pour son proprietaire legitime.
    verif = client.get(f"{API}/opportunities/{cible}", headers=auth("direction"))
    assert verif.status_code == 200


def test_un_tenant_n_affecte_pas_un_departement_d_un_autre(client, other_token, departments):
    """Un identifiant de departement etranger ne doit pas etre accepte a la creation."""
    payload = {
        "email": "fraude@pharmatest-demo.com",
        "full_name": "Tentative inter-tenant",
        "password": "motdepasse2026",
        "department_ids": [departments["COM"].id],
    }
    response = client.post(f"{API}/org/users", json=payload, headers=_headers(other_token))
    assert response.status_code == 404


def test_un_tenant_n_attribue_pas_un_role_d_un_autre(client, other_token):
    payload = {
        "email": "fraude2@pharmatest-demo.com",
        "full_name": "Tentative de rôle étranger",
        "password": "motdepasse2026",
        "role_codes": ["direction"],
    }
    response = client.post(f"{API}/org/users", json=payload, headers=_headers(other_token))
    assert response.status_code == 422
    assert "Rôle inconnu" in response.json()["detail"]


def test_le_journal_d_audit_est_cloisonne(client, auth, other_token):
    medicacom = client.get(f"{API}/admin/audit-logs?limit=200", headers=auth("admin_entreprise")).json()
    pharmatest = client.get(f"{API}/admin/audit-logs?limit=200", headers=_headers(other_token)).json()

    org_medicacom = {e["organization_id"] for e in medicacom}
    org_pharmatest = {e["organization_id"] for e in pharmatest}
    assert not org_medicacom & org_pharmatest


@pytest.mark.parametrize(
    "path",
    [
        "/dashboards/portfolio",
        "/opportunities",
        "/projects",
        "/crossings/datasources",
    ],
)
def test_les_listes_du_second_tenant_sont_vides(client, other_token, path):
    """La nouvelle organisation n'a aucune donnee metier : ses listes sont vides."""
    response = client.get(f"{API}{path}", headers=_headers(other_token))
    assert response.status_code == 200
    assert response.json() == []
