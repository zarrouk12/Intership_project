"""Chaque role obtient exactement les droits que la matrice lui accorde."""
from __future__ import annotations

import pytest

from app.core.rbac import ALL_PERMISSIONS, ROLE_BY_CODE
from tests.conftest import API


# ======================================================================================
# Profil et catalogue
# ======================================================================================

def test_le_profil_expose_permissions_roles_et_perimetre(client, auth):
    response = client.get(f"{API}/auth/me", headers=auth("finance"))
    assert response.status_code == 200
    me = response.json()

    assert me["organization"]["code"] == "MEDICACOM"
    assert me["primary_role"]["code"] == "finance"
    assert "finance.validate" in me["permissions"]
    assert "user.create" not in me["permissions"]
    assert me["scope"]["level"] == "organization"
    assert [d["code"] for d in me["departments"]] == ["FIN"]


def test_le_catalogue_de_permissions_ne_contient_aucun_code_inconnu(client, auth):
    response = client.get(f"{API}/org/permissions", headers=auth("admin_entreprise"))
    assert response.status_code == 200
    codes = {p["code"] for p in response.json()}
    assert codes == set(ALL_PERMISSIONS)


@pytest.mark.parametrize("role", sorted(ROLE_BY_CODE))
def test_chaque_modele_de_role_ne_reference_que_des_permissions_existantes(role):
    template = ROLE_BY_CODE[role]
    inconnues = [code for code in template.permissions if code not in ALL_PERMISSIONS]
    assert not inconnues, f"{role} référence des permissions inconnues : {inconnues}"


# ======================================================================================
# Administration des utilisateurs
# ======================================================================================

def test_admin_entreprise_cree_un_utilisateur_dans_son_organisation(client, auth, db, cleanup):
    from app.models.rbac import User

    payload = {
        "email": "nouvel.arrivant@medicacom.com",
        "full_name": "Nouvel Arrivant",
        "password": "motdepasse2026",
        "job_title": "Analyste",
        "role_codes": ["contributeur_metier"],
    }
    response = client.post(f"{API}/org/users", json=payload, headers=auth("admin_entreprise"))
    assert response.status_code == 201, response.text

    created = response.json()
    cleanup(User, created["id"])
    assert created["organization_id"] == db.scalar(
        __import__("sqlalchemy").select(User.organization_id).where(User.id == created["id"])
    )
    assert [r["code"] for r in created["roles"]] == ["contributeur_metier"]


def test_la_direction_ne_cree_pas_d_utilisateur(client, auth):
    """La Direction pilote le portefeuille ; elle n'administre pas les comptes."""
    payload = {
        "email": "interdit@medicacom.com",
        "full_name": "Compte interdit",
        "password": "motdepasse2026",
    }
    response = client.post(f"{API}/org/users", json=payload, headers=auth("direction"))
    assert response.status_code == 403
    assert "user.create" in response.json()["detail"]


def test_un_admin_entreprise_ne_peut_pas_s_octroyer_le_role_de_plateforme(client, auth):
    """Sans cette barriere, un tenant pourrait s'ouvrir l'acces aux autres organisations."""
    payload = {
        "email": "escalade@medicacom.com",
        "full_name": "Tentative d'escalade",
        "password": "motdepasse2026",
        "role_codes": ["admin_medicacom"],
    }
    response = client.post(f"{API}/org/users", json=payload, headers=auth("admin_entreprise"))
    assert response.status_code == 403
    assert "plateforme" in response.json()["detail"].lower()


def test_un_admin_entreprise_ne_peut_pas_creer_un_role_avec_permission_de_plateforme(client, auth):
    payload = {
        "code": "role_escalade",
        "label": "Rôle d'escalade",
        "permission_codes": ["opportunity.read", "platform.admin"],
    }
    response = client.post(f"{API}/org/roles", json=payload, headers=auth("admin_entreprise"))
    assert response.status_code == 403
    assert "platform.admin" in response.json()["detail"]


def test_un_role_systeme_n_est_pas_modifiable_par_un_admin_entreprise(client, auth):
    roles = client.get(f"{API}/org/roles", headers=auth("admin_entreprise")).json()
    direction = next(r for r in roles if r["code"] == "direction")
    response = client.patch(
        f"{API}/org/roles/{direction['id']}",
        json={"permission_codes": ["organization.read"]},
        headers=auth("admin_entreprise"),
    )
    assert response.status_code == 409
    assert "plateforme" in response.json()["detail"].lower()


def test_un_admin_entreprise_cree_un_role_personnalise(client, auth, db, cleanup):
    from app.models.rbac import Role

    payload = {
        "code": "referent_qualite",
        "label": "Référent qualité",
        "description": "Rôle personnalisé de l'organisation",
        "scope_level": "department",
        "permission_codes": ["opportunity.read", "diagnostic.answer"],
    }
    response = client.post(f"{API}/org/roles", json=payload, headers=auth("admin_entreprise"))
    assert response.status_code == 201, response.text
    created = response.json()
    cleanup(Role, created["id"])
    assert created["is_system"] is False
    assert sorted(created["permission_codes"]) == ["diagnostic.answer", "opportunity.read"]


# ======================================================================================
# Finance
# ======================================================================================

def test_finance_saisit_un_cout(client, auth, db, cleanup):
    from app.models.value import Cost

    response = client.post(
        f"{API}/value/costs",
        json={"label": "Licence de test", "amount_eur": 4200, "category": "run", "recurring": True},
        headers=auth("finance"),
    )
    assert response.status_code == 201, response.text
    cleanup(Cost, response.json()["id"])


def test_finance_ne_modifie_pas_la_recommandation_ia(client, auth):
    """Finance instruit la valeur, pas le choix technique de la solution."""
    opportunities = client.get(f"{API}/opportunities", headers=auth("finance")).json()
    opportunity_id = opportunities[0]["id"]
    response = client.post(f"{API}/opportunities/{opportunity_id}/qualify", headers=auth("finance"))
    assert response.status_code == 403
    assert "recommendation.override" in response.json()["detail"]


def test_finance_ne_pilote_pas_les_projets(client, auth):
    response = client.post(
        f"{API}/projects",
        json={"name": "Projet interdit"},
        headers=auth("finance"),
    )
    assert response.status_code == 403


# ======================================================================================
# AI Lead
# ======================================================================================

def test_ai_lead_requalifie_une_opportunite(client, auth):
    opportunities = client.get(f"{API}/opportunities", headers=auth("ai_lead")).json()
    opportunity_id = opportunities[0]["id"]
    response = client.post(f"{API}/opportunities/{opportunity_id}/qualify", headers=auth("ai_lead"))
    assert response.status_code == 200, response.text
    body = response.json()
    # La recommandation reste explicable : regles declenchees et alternatives ecartees.
    assert body["fired_rules"]
    assert body["alternatives"]


def test_ai_lead_n_administre_pas_les_utilisateurs(client, auth):
    response = client.get(f"{API}/org/users", headers=auth("ai_lead"))
    assert response.status_code == 403


# ======================================================================================
# Data Office et DSI
# ======================================================================================

def test_data_office_gere_les_sources_de_donnees(client, auth, db, cleanup):
    from app.models.architecture import DataSource

    response = client.post(
        f"{API}/crossings/datasources",
        json={"name": "Source de test", "kind": "structuree", "quality_score": 3},
        headers=auth("data_office"),
    )
    assert response.status_code == 201, response.text
    cleanup(DataSource, response.json()["id"])


def test_data_office_ne_gere_pas_le_referentiel_applicatif(client, auth):
    response = client.post(
        f"{API}/crossings/applications",
        json={"name": "Application interdite"},
        headers=auth("data_office"),
    )
    assert response.status_code == 403


def test_dsi_gere_le_referentiel_applicatif(client, auth, db, cleanup):
    from app.models.architecture import Application

    response = client.post(
        f"{API}/crossings/applications",
        json={"name": "Application de test", "category": "ERP", "has_api": True},
        headers=auth("dsi"),
    )
    assert response.status_code == 201, response.text
    cleanup(Application, response.json()["id"])


# ======================================================================================
# PMO
# ======================================================================================

def test_pmo_cree_un_projet(client, auth, db, cleanup):
    from app.models.project import Project

    response = client.post(
        f"{API}/projects",
        json={"name": "Projet de test PMO", "phase": "cadrage"},
        headers=auth("pmo"),
    )
    assert response.status_code == 201, response.text
    cleanup(Project, response.json()["id"])


def test_pmo_ne_valide_pas_les_benefices_financiers(client, auth):
    response = client.post(
        f"{API}/value/benefits",
        json={"label": "Gain interdit", "annual_amount_eur": 1000},
        headers=auth("pmo"),
    )
    assert response.status_code == 403


# ======================================================================================
# Auditeur : lecture seule stricte
# ======================================================================================

def test_l_auditeur_lit_le_journal_d_audit(client, auth):
    response = client.get(f"{API}/admin/audit-logs?limit=5", headers=auth("auditeur"))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/opportunities", {"title": "Interdit"}),
        ("post", "/projects", {"name": "Interdit"}),
        ("post", "/value/costs", {"label": "Interdit", "amount_eur": 1}),
        ("post", "/crossings/datasources", {"name": "Interdit"}),
        ("post", "/org/users", {"email": "x@y.zz", "full_name": "X", "password": "motdepasse2026"}),
        ("post", "/opportunities/prioritize", {"wave_size": 6}),
    ],
)
def test_l_auditeur_ne_peut_rien_ecrire(client, auth, method, path, payload):
    response = getattr(client, method)(f"{API}{path}", json=payload, headers=auth("auditeur"))
    assert response.status_code == 403, f"{method.upper()} {path} a répondu {response.status_code}"


def test_l_auditeur_ne_modifie_pas_une_opportunite(client, auth):
    opportunities = client.get(f"{API}/opportunities", headers=auth("auditeur")).json()
    opportunity_id = opportunities[0]["id"]
    response = client.patch(
        f"{API}/opportunities/{opportunity_id}",
        json={"summary": "modification interdite"},
        headers=auth("auditeur"),
    )
    assert response.status_code == 403


def test_l_auditeur_ne_supprime_pas_une_opportunite(client, auth):
    opportunities = client.get(f"{API}/opportunities", headers=auth("auditeur")).json()
    response = client.delete(
        f"{API}/opportunities/{opportunities[0]['id']}", headers=auth("auditeur")
    )
    assert response.status_code == 403


# ======================================================================================
# Contributeur metier
# ======================================================================================

def test_le_contributeur_ne_voit_pas_le_portefeuille_consolide(client, auth):
    response = client.get(f"{API}/dashboards/portfolio", headers=auth("contributeur"))
    assert response.status_code == 403


def test_le_contributeur_ne_voit_pas_les_donnees_financieres(client, auth):
    response = client.get(f"{API}/value/portfolio", headers=auth("contributeur"))
    assert response.status_code == 403
