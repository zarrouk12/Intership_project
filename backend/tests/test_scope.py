"""Le perimetre departemental limite ce qui est visible et ce qui est modifiable."""
from __future__ import annotations

from tests.conftest import API


def test_un_responsable_ne_voit_que_son_departement(client, auth):
    commercial = client.get(f"{API}/opportunities", headers=auth("resp_commercial")).json()
    production = client.get(f"{API}/opportunities", headers=auth("resp_production")).json()

    assert commercial, "Le responsable Commercial devrait voir ses opportunités"
    assert production, "Le responsable Production devrait voir ses opportunités"
    assert {o["department_name"] for o in commercial} == {"Commercial"}
    assert {o["department_name"] for o in production} == {"Production"}
    assert not {o["id"] for o in commercial} & {o["id"] for o in production}


def test_la_direction_voit_tous_les_departements(client, auth):
    toutes = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    commercial = client.get(f"{API}/opportunities", headers=auth("resp_commercial")).json()
    assert len(toutes) > len(commercial)
    assert len({o["department_name"] for o in toutes}) > 1


def test_un_responsable_cree_dans_son_departement(client, auth, departments, cleanup):
    from app.models.opportunity import Opportunity

    payload = {
        "title": "Besoin commercial de test",
        "summary": "Créée par le responsable Commercial",
        "department_id": departments["COM"].id,
    }
    response = client.post(f"{API}/opportunities", json=payload, headers=auth("resp_commercial"))
    assert response.status_code == 201, response.text
    cleanup(Opportunity, response.json()["id"])


def test_un_responsable_ne_cree_pas_dans_un_autre_departement(client, auth, departments):
    payload = {
        "title": "Intrusion en Production",
        "department_id": departments["PRD"].id,
    }
    response = client.post(f"{API}/opportunities", json=payload, headers=auth("resp_commercial"))
    assert response.status_code == 403
    assert "périmètre" in response.json()["detail"].lower()


def test_un_responsable_ne_modifie_pas_l_opportunite_d_un_autre_departement(
    client, auth, departments
):
    toutes = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    production = next(o for o in toutes if o["department_id"] == departments["PRD"].id)

    response = client.patch(
        f"{API}/opportunities/{production['id']}",
        json={"summary": "modification hors périmètre"},
        headers=auth("resp_commercial"),
    )
    assert response.status_code == 403


def test_une_opportunite_hors_perimetre_est_introuvable_en_lecture(client, auth, departments):
    """Hors perimetre, la lecture renvoie 404 : on ne confirme pas l'existence de l'objet."""
    toutes = client.get(f"{API}/opportunities", headers=auth("direction")).json()
    production = next(o for o in toutes if o["department_id"] == departments["PRD"].id)

    response = client.get(f"{API}/opportunities/{production['id']}", headers=auth("resp_commercial"))
    assert response.status_code == 404


def test_un_responsable_lit_les_dependances_transverses(client, auth):
    """Le perimetre restreint l'ecriture, pas la collaboration interservices."""
    response = client.get(f"{API}/crossings/dependencies", headers=auth("resp_commercial"))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_le_tableau_de_bord_departemental_est_borne_au_perimetre(client, auth):
    commercial = client.get(f"{API}/dashboards/department", headers=auth("resp_commercial")).json()
    direction = client.get(f"{API}/dashboards/department", headers=auth("direction")).json()

    assert commercial["scope"]["level"] == "department"
    assert commercial["scope"]["department_names"] == ["Commercial"]
    assert direction["scope"]["is_organization_wide"] is True
    assert len(direction["scope"]["department_names"]) > 1

    opportunites_commercial = commercial["kpis"][0]["value"]
    opportunites_direction = direction["kpis"][0]["value"]
    assert opportunites_commercial < opportunites_direction


def test_le_portefeuille_est_filtre_par_perimetre(client, auth):
    commercial = client.get(f"{API}/dashboards/portfolio", headers=auth("resp_commercial")).json()
    direction = client.get(f"{API}/dashboards/portfolio", headers=auth("direction")).json()
    assert len(commercial) < len(direction)
    assert {row["department_name"] for row in commercial} == {"Commercial"}


def test_les_projets_sont_filtres_par_perimetre(client, auth, departments):
    projets = client.get(f"{API}/projects", headers=auth("resp_commercial")).json()
    hors_perimetre = [p for p in projets if p["department_id"] != departments["COM"].id]
    assert not hors_perimetre
