"""Point d'entree de l'API Medicacom AOI Transformation."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import (
    admin,
    auth,
    crossings,
    dashboards,
    diagnostic,
    opportunities,
    organization,
    projects,
    sheets,
    value,
)

DESCRIPTION = """
Plateforme de pilotage de l'adoption de l'IA pour l'industrie pharmaceutique.

Parcours couvert : diagnostic TOGAF (M2/M5) -> qualification de solution (M4) ->
priorisation (M7) -> fiche projet (M8) -> suivi du cycle de vie (M9) -> valeur et ROI (M10).

Toutes les donnees metier sont cloisonnees par organisation : le jeton JWT porte
l'identifiant du tenant et aucune requete ne peut en sortir.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix=settings.API_V1_PREFIX)
api.include_router(auth.router)
api.include_router(organization.router)
api.include_router(diagnostic.router)
api.include_router(opportunities.router)
api.include_router(crossings.router)
api.include_router(projects.router)
api.include_router(sheets.router)
api.include_router(value.router)
api.include_router(dashboards.router)
api.include_router(admin.router)

app.include_router(api)


@app.get("/health", tags=["Systeme"], summary="Sonde de sante")
def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "1.0.0"}


@app.get("/", tags=["Systeme"], summary="Racine")
def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }
