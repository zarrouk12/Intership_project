"""Garde-fous structurels sur les routes.

Ces tests ne verifient pas un comportement metier mais une propriete de l'API :
qu'aucun endpoint ne puisse etre ajoute sans protection, et qu'aucune dependance ne se
transforme silencieusement en parametre de requete. Ce second cas s'est deja produit :
une annotation `Scope` non importee dans un router avait ete interpretee par FastAPI
comme un parametre `?scope=`, rendant l'endpoint inutilisable sans lever d'erreur.
"""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app

#: Endpoints volontairement ouverts a tout utilisateur authentifie, ou publics.
#: `/auth/demo-accounts` est public par necessite : il alimente l'aide affichee avant
#: toute connexion. Sa protection n'est pas une permission mais l'environnement — il
#: repond 404 des que ENVIRONMENT n'est pas un environnement de developpement.
OUVERTS = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/token"),
    ("GET", "/api/v1/auth/demo-accounts"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/password"),
    ("GET", "/api/v1/org/scope"),
    ("GET", "/api/v1/admin/notifications"),
    ("POST", "/api/v1/admin/notifications/{notification_id}/read"),
    ("GET", "/health"),
    ("GET", "/"),
}

#: Noms reserves aux dependances : jamais un parametre de requete.
NOMS_DE_DEPENDANCE = {"db", "scope", "current_user", "tenant_id", "ip"}


def _routes() -> list[tuple[str, APIRoute]]:
    out = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            out.append((method, route))
    return out


def test_aucun_endpoint_n_est_expose_sans_controle():
    """Chaque route porte soit une permission, soit une dispense explicite."""
    non_proteges = []
    for method, route in _routes():
        if (method, route.path) in OUVERTS:
            continue
        noms = {d.call.__name__ for d in route.dependant.dependencies if d.call}
        sous_noms = {
            sd.call.__name__
            for d in route.dependant.dependencies
            for sd in d.dependencies
            if sd.call
        }
        signature = str(route.dependant.call.__annotations__) + str(route.endpoint.__defaults__)
        protege = (
            "_checker" in noms
            or "_checker" in sous_noms
            or "require_platform_admin" in noms
            or "_checker" in signature
        )
        if not protege:
            non_proteges.append(f"{method} {route.path}")

    assert not non_proteges, (
        "Endpoints sans contrôle de permission :\n  " + "\n  ".join(sorted(non_proteges))
    )


def test_aucune_dependance_n_est_traitee_comme_un_parametre_de_requete():
    """Une dependance mal importee devient un parametre `?nom=` sans lever d'erreur."""
    fautes = []
    for method, route in _routes():
        for param in route.dependant.query_params:
            if param.name in NOMS_DE_DEPENDANCE:
                fautes.append(f"{method} {route.path} — paramètre de requête « {param.name} »")
    assert not fautes, (
        "Dépendances transformées en paramètres de requête (import manquant ?) :\n  "
        + "\n  ".join(sorted(fautes))
    )


def test_aucune_dependance_n_est_traitee_comme_un_corps_de_requete():
    fautes = []
    for method, route in _routes():
        for param in route.dependant.body_params:
            if param.name in NOMS_DE_DEPENDANCE:
                fautes.append(f"{method} {route.path} — corps « {param.name} »")
    assert not fautes, "Dépendances transformées en corps de requête :\n  " + "\n  ".join(fautes)


def test_toutes_les_routes_metier_sont_sous_le_prefixe_versionne():
    hors_prefixe = [
        f"{method} {route.path}"
        for method, route in _routes()
        if not route.path.startswith("/api/v1") and route.path not in ("/health", "/")
    ]
    assert not hors_prefixe, f"Routes hors préfixe versionné : {hors_prefixe}"
