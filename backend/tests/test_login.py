"""Connexion : jeton, distinction des erreurs et aide aux comptes de démonstration.

L'écran de connexion ne code aucun compte en dur. Il interroge `/auth/demo-accounts`,
qui n'existe qu'en développement. Ces tests vérifient que la bascule en production fait
bien disparaître l'endpoint, sans quoi une liste de comptes fuiterait par l'interface.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import API, PASSWORD


# ======================================================================================
# Authentification
# ======================================================================================

def test_la_connexion_emet_un_jeton(client):
    response = client.post(
        f"{API}/auth/login",
        json={"email": "marwen.b@medicacom.com", "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_un_mot_de_passe_errone_repond_401(client):
    """401 et non 403 : l'interface distingue la faute de frappe du compte désactivé."""
    response = client.post(
        f"{API}/auth/login",
        json={"email": "marwen.b@medicacom.com", "password": "mauvais-mot-de-passe"},
    )
    assert response.status_code == 401


def test_un_email_inconnu_repond_401(client):
    """Même code qu'un mot de passe erroné : on n'indique pas si le compte existe."""
    response = client.post(
        f"{API}/auth/login",
        json={"email": "inconnu@medicacom.com", "password": PASSWORD},
    )
    assert response.status_code == 401


def test_un_email_malforme_repond_422(client):
    response = client.post(f"{API}/auth/login", json={"email": "pas-un-email", "password": PASSWORD})
    assert response.status_code == 422


def test_un_compte_desactive_repond_403(client, auth, db):
    """Le compte désactivé mérite son propre message : l'utilisateur ne peut rien y faire."""
    from sqlalchemy import select

    from app.models.rbac import User

    cible = db.scalar(select(User).where(User.email == "audit@medicacom.com"))
    cible.is_active = False
    db.commit()
    try:
        response = client.post(
            f"{API}/auth/login", json={"email": "audit@medicacom.com", "password": PASSWORD}
        )
        assert response.status_code == 403
        assert "désactivé" in response.json()["detail"].lower()
    finally:
        cible.is_active = True
        db.commit()


def test_la_connexion_horodate_la_derniere_visite(client, db):
    from sqlalchemy import select

    from app.models.rbac import User

    client.post(f"{API}/auth/login", json={"email": "m.dupuis@medicacom.com", "password": PASSWORD})
    db.expire_all()
    utilisateur = db.scalar(select(User).where(User.email == "m.dupuis@medicacom.com"))
    assert utilisateur.last_login_at is not None


# ======================================================================================
# Aide aux comptes de démonstration
# ======================================================================================

def test_l_aide_liste_les_comptes_en_developpement(client):
    response = client.get(f"{API}/auth/demo-accounts")
    assert response.status_code == 200

    body = response.json()
    assert body["accounts"], "Le jeu de démonstration doit exposer ses comptes"

    emails = {compte["email"] for compte in body["accounts"]}
    assert "marwen.b@medicacom.com" in emails

    premier = body["accounts"][0]
    assert premier["role_label"]
    assert premier["scope_label"]


def test_l_aide_ne_contient_aucun_compte_desactive(client, db):
    from sqlalchemy import select

    from app.models.rbac import User

    cible = db.scalar(select(User).where(User.email == "audit@medicacom.com"))
    cible.is_active = False
    db.commit()
    try:
        emails = {c["email"] for c in client.get(f"{API}/auth/demo-accounts").json()["accounts"]}
        assert "audit@medicacom.com" not in emails
    finally:
        cible.is_active = True
        db.commit()


def test_l_aide_disparait_en_production(client, monkeypatch):
    """La mise en production suffit : le frontend n'a rien à changer."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    response = client.get(f"{API}/auth/demo-accounts")
    assert response.status_code == 404


def test_le_mot_de_passe_n_est_publie_que_s_il_est_configure(client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_PASSWORD", "")
    assert client.get(f"{API}/auth/demo-accounts").json()["password"] is None

    monkeypatch.setattr(settings, "DEMO_PASSWORD", PASSWORD)
    assert client.get(f"{API}/auth/demo-accounts").json()["password"] == PASSWORD


def test_l_aide_ne_demande_aucune_authentification(client):
    """Elle s'affiche avant la connexion : elle ne peut pas exiger de jeton."""
    response = client.get(f"{API}/auth/demo-accounts")
    assert response.status_code == 200


@pytest.mark.parametrize("environnement", ["production", "prod", "staging", "PRODUCTION"])
def test_tout_environnement_autre_que_developpement_ferme_l_aide(
    client, monkeypatch, environnement
):
    monkeypatch.setattr(settings, "ENVIRONMENT", environnement)
    assert client.get(f"{API}/auth/demo-accounts").status_code == 404


@pytest.mark.parametrize("environnement", ["development", "dev", "local", "Development"])
def test_les_alias_de_developpement_sont_reconnus(client, monkeypatch, environnement):
    monkeypatch.setattr(settings, "ENVIRONMENT", environnement)
    assert client.get(f"{API}/auth/demo-accounts").status_code == 200
