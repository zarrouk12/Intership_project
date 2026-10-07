"""M2 / M5 — instruction du diagnostic et calcul du readiness.

Le point sensible : une dimension non encore evaluee ne doit pas compter comme un zero.
Elle sort du score et fait baisser le taux de completion, ce qui donne son sens a
l'action « Poursuivre le diagnostic ».
"""
from __future__ import annotations

import pytest

from tests.conftest import API


@pytest.fixture
def campaign(client, auth):
    assessments = client.get(f"{API}/diagnostic/assessments", headers=auth("direction")).json()
    assert assessments, "Lancez `python -m app.seed` avant les tests."
    return assessments[0]


@pytest.fixture
def restore_response(client, auth, db):
    """Remet une reponse dans son etat initial a la fin du test."""
    saved: list[tuple[int, dict]] = []

    def _remember(response: dict) -> None:
        saved.append(
            (
                response["id"],
                {
                    "score": response["score"],
                    "weight": response["weight"],
                    "confidence": response["confidence"],
                    "evidence": response["evidence"],
                },
            )
        )

    yield _remember

    for response_id, payload in reversed(saved):
        client.patch(f"{API}/diagnostic/responses/{response_id}", json=payload, headers=auth("dsi"))


# ======================================================================================
# Calcul
# ======================================================================================

def test_le_taux_de_completion_est_calcule_et_non_saisi(client, auth):
    readiness = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()

    assert readiness["total_count"] > readiness["answered_count"], (
        "Le jeu de démonstration doit comporter des dimensions restant à instruire"
    )
    attendu = readiness["answered_count"] / readiness["total_count"] * 100
    assert readiness["completion_rate"] == pytest.approx(attendu, abs=0.1)


def test_une_dimension_non_instruite_ne_compte_pas_comme_un_zero(client, auth):
    """Sans cette regle, ouvrir une nouvelle dimension ferait chuter le score."""
    readiness = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    pending = readiness["pending_dimensions"]

    assert pending, "Le jeu de démonstration doit comporter des dimensions à instruire"
    for dimension in pending:
        assert dimension["is_answered"] is False
        assert dimension["confidence"] == 0
        # Elle n'apporte rien au rapport, donc ne le tire pas vers le bas.
        assert dimension["weighted_score"] == 0
        assert dimension["max_weighted"] == 0
        # Une dimension non mesuree n'est ni bloquante ni en vigilance.
        assert dimension["is_blocking"] is False
        assert dimension["is_watch"] is False

    # Le score reste celui des seules dimensions evaluees.
    assert readiness["global_score"] == pytest.approx(62.0, abs=0.5)


def test_les_moyennes_d_axe_ignorent_les_dimensions_non_instruites(client, auth):
    readiness = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    assert readiness["technical_average"] == pytest.approx(2.81, abs=0.02)
    assert readiness["business_average"] == pytest.approx(3.12, abs=0.02)


# ======================================================================================
# Instruction d'une dimension
# ======================================================================================

def test_instruire_une_dimension_fait_progresser_la_completion(
    client, auth, campaign, restore_response
):
    avant = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    detail = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}", headers=auth("direction")
    ).json()

    cible = next(r for r in detail["responses"] if r["confidence"] == 0)
    restore_response(cible)

    reponse = client.patch(
        f"{API}/diagnostic/responses/{cible['id']}",
        json={"score": 3, "confidence": 0.75, "evidence": "Atelier du 30 septembre 2026."},
        headers=auth("dsi"),
    )
    assert reponse.status_code == 200, reponse.text

    apres = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    assert apres["answered_count"] == avant["answered_count"] + 1
    assert apres["completion_rate"] > avant["completion_rate"]
    assert len(apres["pending_dimensions"]) == len(avant["pending_dimensions"]) - 1


def test_instruire_une_dimension_modifie_le_score(client, auth, campaign, restore_response):
    """Une dimension notee entre dans le calcul, contrairement a une dimension vierge."""
    avant = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    detail = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}", headers=auth("direction")
    ).json()

    cible = next(r for r in detail["responses"] if r["confidence"] == 0)
    restore_response(cible)

    # Une note de 5 sur une dimension jusque-la hors calcul doit relever le score.
    client.patch(
        f"{API}/diagnostic/responses/{cible['id']}",
        json={"score": 5, "confidence": 1.0, "evidence": "Chaîne MLOps industrialisée."},
        headers=auth("dsi"),
    )
    apres = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    assert apres["global_score"] > avant["global_score"]


def test_une_dimension_critique_sous_le_seuil_devient_bloquante(
    client, auth, campaign, restore_response
):
    detail = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}", headers=auth("direction")
    ).json()
    cible = next(r for r in detail["responses"] if r["confidence"] == 0 and r["is_critical"])
    restore_response(cible)

    client.patch(
        f"{API}/diagnostic/responses/{cible['id']}",
        json={"score": 1, "confidence": 0.75, "evidence": "Aucun environnement de mise en service."},
        headers=auth("dsi"),
    )
    apres = client.get(f"{API}/diagnostic/readiness", headers=auth("direction")).json()
    bloquantes = {d["dimension_code"] for d in apres["blocking_dimensions"]}
    assert cible["dimension_code"] in bloquantes


# ======================================================================================
# Droits
# ======================================================================================

@pytest.mark.parametrize("role", ["auditeur", "direction", "finance"])
def test_repondre_au_diagnostic_exige_la_permission(client, auth, campaign, role):
    detail = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}", headers=auth("direction")
    ).json()
    cible = detail["responses"][0]

    response = client.patch(
        f"{API}/diagnostic/responses/{cible['id']}",
        json={"score": 5},
        headers=auth(role),
    )
    assert response.status_code == 403
    assert "diagnostic.answer" in response.json()["detail"]


def test_le_contributeur_peut_repondre_au_diagnostic(client, auth, campaign, restore_response):
    """Repondre aux questionnaires assignes est le coeur du role de contributeur."""
    detail = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}", headers=auth("direction")
    ).json()
    cible = detail["responses"][0]
    restore_response(cible)

    response = client.patch(
        f"{API}/diagnostic/responses/{cible['id']}",
        json={"evidence": "Complété par le contributeur métier."},
        headers=auth("contributeur"),
    )
    assert response.status_code == 200, response.text


def test_la_campagne_d_un_autre_tenant_est_introuvable(client, other_token, campaign):
    response = client.get(
        f"{API}/diagnostic/assessments/{campaign['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404
