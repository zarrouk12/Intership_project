# Backend — Medicacom AOI Transformation

API FastAPI, SQLAlchemy 2.0 déclaratif, migrations Alembic, PostgreSQL.

## Installation

```bash
python -m venv .venv
```

Activez ensuite l'environnement virtuel, avec la commande de votre terminal :

| Terminal | Commande |
|---|---|
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Invite de commandes (cmd) | `.venv\Scripts\activate.bat` |
| Git Bash sous Windows | `source .venv/Scripts/activate` |
| Linux et macOS | `source .venv/bin/activate` |

```bash
pip install -r requirements.txt
cp .env.example .env
```

Tant que l'environnement n'est pas activé, `uvicorn`, `alembic` et `pytest` ne sont pas
dans le `PATH` : le terminal répond que la commande n'est pas reconnue. Deux issues, au
choix — activer l'environnement, ou appeler les exécutables du venv par leur chemin :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest
```

Si PowerShell refuse d'exécuter `Activate.ps1`, la politique d'exécution le bloque :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Variables du `.env` :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | URL SQLAlchemy, par défaut `postgresql+psycopg2://odoo:odoo@localhost:5432/medicacom` |
| `SECRET_KEY` | Clé de signature des JWT — à remplacer en production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité du jeton (720 par défaut) |
| `BACKEND_CORS_ORIGINS` | Origines autorisées, séparées par des virgules |
| `FIRST_SUPERUSER_EMAIL` / `FIRST_SUPERUSER_PASSWORD` | Compte administrateur créé par le seed |
| `ENVIRONMENT` | `development` ou `production` — voir ci-dessous |
| `DEMO_PASSWORD` | Mot de passe commun aux comptes de démonstration, publié par l'aide de connexion |

### Passage en production

L'écran de connexion propose une aide listant les comptes de démonstration. Elle est
alimentée par `GET /auth/demo-accounts`, qui **n'existe qu'en développement** : dès que
`ENVIRONMENT` vaut autre chose, l'endpoint répond 404 et le bloc disparaît de
l'interface. Aucun compte n'est écrit en dur côté React, donc rien à modifier dans le
frontend pour livrer.

```ini
ENVIRONMENT=production
DEMO_PASSWORD=
SECRET_KEY=<une chaîne longue et aléatoire>
```

Videz `DEMO_PASSWORD` : même en développement, un champ vide empêche la publication du
mot de passe, la liste restant alors purement informative.

## Migrations

```bash
alembic upgrade head                            # applique le schéma
alembic revision --autogenerate -m "message"    # après modification des modèles
alembic downgrade -1                            # revient d'une révision
```

`alembic/env.py` lit l'URL depuis la configuration applicative : rien n'est codé en
dur dans `alembic.ini`.

## Données de démonstration

```bash
python -m app.seed            # ne fait rien si l'organisation existe déjà
python -m app.seed --reset    # vide les tables métier puis reconstruit
```

## Lancement

```bash
uvicorn app.main:app --reload --port 8000
```

- Documentation interactive : `http://127.0.0.1:8000/docs`
- Schéma OpenAPI : `http://127.0.0.1:8000/api/v1/openapi.json`
- Sonde de santé : `http://127.0.0.1:8000/health`

## Organisation du code

| Répertoire | Contenu |
|---|---|
| `app/core` | Configuration Pydantic Settings, moteur et session SQLAlchemy, hachage bcrypt et JWT |
| `app/models` | Modèles déclaratifs, un module par domaine, plus les référentiels de codes dans `base.py` |
| `app/schemas` | Schémas Pydantic v2, séparés en variantes `Create`, `Update` et `Out` |
| `app/api/deps.py` | Dépendances communes : session, utilisateur courant, contrôle de permissions, isolation tenant |
| `app/api/routers` | Un router par module fonctionnel |
| `app/services` | Logique métier pure, sans dépendance à FastAPI, donc testable isolément |

## Isolation multi-tenant

`get_tenant_id` dérive l'organisation depuis le jeton, jamais depuis le corps de la
requête. `get_or_404` vérifie l'appartenance de chaque entité au tenant courant avant
de la renvoyer : une ressource d'une autre organisation répond 404, pas 403, afin de
ne pas divulguer son existence.

## Contrôle d'accès

`require_permissions("code")` construit une dépendance qui vérifie les permissions
portées par les rôles de l'utilisateur. Les superutilisateurs passent tous les
contrôles. Permissions disponibles :

`org.manage`, `diagnostic.write`, `opportunity.write`, `architecture.write`,
`project.write`, `project.approve`, `sheet.write`, `sheet.approve`, `value.write`,
`admin.audit`.

## Journal d'audit

`app/services/audit.py` expose `log_action` pour une création ou une suppression et
`log_update` pour une modification. `log_update` photographie l'entité avant
changement, compare les colonnes et n'enregistre que le delta réel — une requête qui
ne change rien n'écrit pas de ligne. Les valeurs sont normalisées en JSON (dates en
ISO, décimaux en flottants).

## Explicabilité

Trois endpoints renvoient le raisonnement et pas seulement le résultat :

| Endpoint | Ce qu'il expose |
|---|---|
| `GET /api/v1/opportunities/{id}/score` | Chaque critère avec sa valeur, son poids, sa contribution, le risque brut et la pénalité |
| `POST /api/v1/opportunities/{id}/qualify` | Règles satisfaites et manquées, alternatives écartées avec leur score, garde-fous |
| `GET /api/v1/diagnostic/readiness` | Chaque dimension avec sa note, son poids, sa confiance, sa preuve et son statut bloquant |

`POST /api/v1/opportunities/qualify/simulate` permet de tester une qualification sans
rien enregistrer, ce qui sert à guider la saisie du questionnaire.
