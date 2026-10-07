"""M3 / M4 / M7 — cycle de vie complet d'une opportunité et priorisation pondérée.

Deux points sont vérifiés en particulier :
  - la modification relance la qualification et le score, elle ne se contente pas
    d'écrire des champs ;
  - la priorisation tient réellement compte des pondérations transmises, sans quoi le
    bouton « Recalculer la priorisation » ne pourrait jamais changer un classement.
"""
from __future__ import annotations

import pytest

from tests.conftest import API


@pytest.fixture
def departements(client, auth):
    rows = client.get(f"{API}/org/departments", headers=auth("admin_entreprise")).json()
    return {d["code"]: d for d in rows}


@pytest.fixture
def opportunite(client, auth, departements, db):
    """Crée une opportunité jetable dans le département Commercial."""
    from app.models.opportunity import Opportunity

    payload = {
        "title": "Opportunité de test CRUD",
        "summary": "Créée par la suite de tests",
        "department_id": departements["COM"]["id"],
        "data_available": True,
        "data_structured": True,
        "data_quality": 4,
        "ground_truth_available": True,
        "impact_business": 60,
        "impact_financial": 50,
        "feasibility": 55,
        "alignment": 50,
    }
    response = client.post(f"{API}/opportunities", json=payload, headers=auth("resp_commercial"))
    assert response.status_code == 201, response.text
    created = response.json()

    yield created

    # Nettoyage : l'opportunité peut avoir déjà été supprimée par le test.
    if db.get(Opportunity, created["id"]) is not None:
        client.delete(f"{API}/opportunities/{created['id']}", headers=auth("resp_commercial"))
        db.expire_all()


# ======================================================================================
# Création
# ======================================================================================

def test_creer_une_opportunite_la_qualifie_et_la_score(client, auth, opportunite):
    """La création n'enregistre pas un formulaire : elle produit une recommandation."""
    assert opportunite["code"].startswith("OPP-")
    assert opportunite["recommendation"] is not None
    assert opportunite["recommendation"]["ai_type"] == "ia_classique"
    assert opportunite["recommendation"]["fired_rules"]
    assert opportunite["priority_score"] > 0

    detail = client.get(f"{API}/opportunities/{opportunite['id']}", headers=auth("resp_commercial"))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Opportunité de test CRUD"


def test_une_creation_apparait_dans_la_liste_et_le_portefeuille(client, auth, opportunite):
    liste = client.get(f"{API}/opportunities", headers=auth("resp_commercial")).json()
    assert opportunite["id"] in {o["id"] for o in liste}

    portefeuille = client.get(f"{API}/dashboards/portfolio", headers=auth("direction")).json()
    assert opportunite["id"] in {row["id"] for row in portefeuille}


# ======================================================================================
# Modification
# ======================================================================================

def test_modifier_les_scores_recalcule_la_priorite(client, auth, opportunite):
    avant = opportunite["priority_score"]
    response = client.patch(
        f"{API}/opportunities/{opportunite['id']}",
        json={"impact_business": 95, "impact_financial": 90},
        headers=auth("resp_commercial"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["priority_score"] > avant


def test_modifier_les_reponses_relance_la_qualification(client, auth, opportunite):
    """Passer d'un besoin de prédiction à un besoin de rédaction doit changer le type."""
    assert opportunite["recommendation"]["ai_type"] == "ia_classique"

    response = client.patch(
        f"{API}/opportunities/{opportunite['id']}",
        json={
            "data_structured": False,
            "unstructured_text": True,
            "content_generation": True,
            "human_in_the_loop": True,
        },
        headers=auth("resp_commercial"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["recommendation"]["ai_type"] == "generative"


def test_une_modification_partielle_ne_touche_pas_les_autres_champs(client, auth, opportunite):
    """Le formulaire n'envoie que le delta : le reste doit rester intact."""
    response = client.patch(
        f"{API}/opportunities/{opportunite['id']}",
        json={"summary": "Résumé mis à jour"},
        headers=auth("resp_commercial"),
    )
    assert response.status_code == 200
    apres = response.json()
    assert apres["summary"] == "Résumé mis à jour"
    assert apres["title"] == opportunite["title"]
    assert apres["impact_business"] == opportunite["impact_business"]


def test_la_modification_est_tracee_dans_l_audit(client, auth, opportunite):
    client.patch(
        f"{API}/opportunities/{opportunite['id']}",
        json={"title": "Intitulé corrigé"},
        headers=auth("resp_commercial"),
    )
    entrees = client.get(
        f"{API}/admin/audit-logs/opportunity/{opportunite['id']}", headers=auth("admin_entreprise")
    ).json()
    actions = {e["action"] for e in entrees}
    assert "create" in actions
    assert "update" in actions

    modification = next(e for e in entrees if e["action"] == "update")
    assert modification["new_value"]["title"] == "Intitulé corrigé"
    assert modification["old_value"]["title"] == "Opportunité de test CRUD"


# ======================================================================================
# Suppression
# ======================================================================================

def test_supprimer_une_opportunite(client, auth, opportunite, db):
    response = client.delete(
        f"{API}/opportunities/{opportunite['id']}", headers=auth("resp_commercial")
    )
    assert response.status_code == 204

    db.expire_all()
    apres = client.get(f"{API}/opportunities/{opportunite['id']}", headers=auth("resp_commercial"))
    assert apres.status_code == 404

    liste = client.get(f"{API}/opportunities", headers=auth("resp_commercial")).json()
    assert opportunite["id"] not in {o["id"] for o in liste}


def test_la_suppression_est_tracee(client, auth, opportunite, db):
    client.delete(f"{API}/opportunities/{opportunite['id']}", headers=auth("resp_commercial"))
    db.expire_all()
    entrees = client.get(
        f"{API}/admin/audit-logs/opportunity/{opportunite['id']}", headers=auth("admin_entreprise")
    ).json()
    assert "delete" in {e["action"] for e in entrees}


@pytest.mark.parametrize("role", ["auditeur", "finance", "direction"])
def test_supprimer_exige_la_permission(client, auth, opportunite, role):
    response = client.delete(f"{API}/opportunities/{opportunite['id']}", headers=auth(role))
    assert response.status_code == 403


# ======================================================================================
# Priorisation pondérée (M7)
# ======================================================================================

def _classement(client, auth) -> dict[int, int]:
    rows = client.get(f"{API}/dashboards/portfolio", headers=auth("direction")).json()
    return {row["id"]: row["priority_rank"] for row in rows}


@pytest.fixture
def classement_par_defaut(client, auth):
    """Établit le classement par défaut avant le test, et le rétablit après.

    Sans la remise à zéro initiale, le test dépendrait des pondérations laissées par
    une exécution précédente : appliquer deux fois les mêmes poids ne déplacerait rien
    et le test échouerait sans qu'aucune régression n'existe.
    """
    remettre = lambda: client.post(  # noqa: E731
        f"{API}/opportunities/prioritize", json={"wave_size": 6}, headers=auth("direction")
    )
    remettre()
    yield
    remettre()


def test_les_ponderations_changent_le_classement(client, auth, classement_par_defaut):
    """Sans cet effet, le bouton de repriorisation ne pourrait rien produire."""
    avant = _classement(client, auth)

    response = client.post(
        f"{API}/opportunities/prioritize",
        json={
            # L'impact financier écrase tout, l'impact métier ne pèse presque plus.
            "weights": {"impact_business": 0.02, "impact_financial": 0.5},
            "wave_size": 6,
        },
        headers=auth("direction"),
    )
    assert response.status_code == 200, response.text
    apres = {item["id"]: item["priority_rank"] for item in response.json()["items"]}

    deplacements = [oid for oid, rang in apres.items() if avant.get(oid) != rang]
    assert deplacements, "Modifier les pondérations doit déplacer au moins une opportunité"


def test_les_ponderations_sont_renormalisees(client, auth, classement_par_defaut):
    """La somme des poids n'a pas à valoir 1 : seul leur rapport compte."""
    response = client.post(
        f"{API}/opportunities/prioritize",
        json={"weights": {"impact_business": 2, "impact_financial": 2}, "wave_size": 6},
        headers=auth("direction"),
    )
    poids = response.json()["weights"]
    assert sum(poids.values()) == pytest.approx(1.0, abs=0.001)
    assert poids["impact_business"] == pytest.approx(poids["impact_financial"], abs=0.001)


def test_la_taille_de_vague_est_respectee(client, auth, classement_par_defaut):
    response = client.post(
        f"{API}/opportunities/prioritize", json={"wave_size": 4}, headers=auth("direction")
    )
    items = response.json()["items"]
    for item in items:
        assert item["wave"] == (item["priority_rank"] - 1) // 4 + 1


def test_prioriser_exige_la_permission(client, auth):
    response = client.post(
        f"{API}/opportunities/prioritize", json={"wave_size": 6}, headers=auth("pmo")
    )
    assert response.status_code == 403
    assert "portfolio.prioritize" in response.json()["detail"]
