# Medicacom — AOI Transformation

Plateforme SaaS de pilotage de l'adoption de l'IA pour l'industrie pharmaceutique.
Elle couvre le parcours complet : **diagnostic TOGAF → qualification de solution →
priorisation → fiche projet → suivi du cycle de vie → ROI**.

```
backend/    API FastAPI + SQLAlchemy 2 + Alembic (PostgreSQL)
frontend/   React 18 + Vite + TypeScript + TanStack Query + Recharts
```

---

## Prérequis

| Outil | Version testée |
|---|---|
| Python | 3.12 |
| Node.js | 24 |
| PostgreSQL | 14 ou supérieur |

---

## Démarrage rapide

### 1. Base de données

L'application attend une base `medicacom` accessible avec le rôle `odoo` :

```sql
CREATE DATABASE medicacom;
```

L'URL SQLAlchemy par défaut est `postgresql+psycopg2://odoo:odoo@localhost:5432/medicacom`.

### 2. Backend

```bash
cd backend
python -m venv .venv
```

**Activez l'environnement virtuel** avant toute autre commande. La syntaxe dépend du
terminal : sans activation, `uvicorn`, `alembic` et `pytest` restent introuvables.

| Terminal | Commande d'activation |
|---|---|
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Invite de commandes (cmd) | `.venv\Scripts\activate.bat` |
| Git Bash sous Windows | `source .venv/Scripts/activate` |
| Linux et macOS | `source .venv/bin/activate` |

L'invite affiche alors `(.venv)` en tête de ligne. La suite est identique sur tous les
systèmes :

```bash
pip install -r requirements.txt
cp .env.example .env            # ajustez DATABASE_URL et SECRET_KEY

alembic upgrade head            # crée le schéma
python -m app.seed              # jeu de démonstration pharmaceutique

uvicorn app.main:app --reload --port 8000
```

> **PowerShell refuse d'exécuter le script d'activation ?** La politique d'exécution le
> bloque. Autorisez les scripts locaux pour votre compte, une fois pour toutes :
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
>
> **Vous préférez ne rien activer ?** Appelez les exécutables du venv directement, ce qui
> fonctionne dans n'importe quel terminal :
> ```powershell
> .\.venv\Scripts\python.exe -m pip install -r requirements.txt
> .\.venv\Scripts\alembic.exe upgrade head
> .\.venv\Scripts\python.exe -m app.seed
> .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
> ```

L'API écoute sur `http://127.0.0.1:8000`. La documentation OpenAPI est servie sur
`/docs` et le schéma sur `/api/v1/openapi.json`.

Pour reconstruire les données de démonstration à zéro :

```bash
python -m app.seed --reset
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env            # facultatif : le proxy Vite pointe déjà sur le port 8000
npm run dev
```

L'interface est servie sur `http://localhost:5173`. Les appels `/api` sont relayés
vers le backend par le proxy de développement de Vite.

### 4. Connexion

Treize comptes de démonstration, un par rôle fonctionnel, tous avec le mot de passe
`medicacom2026` :

| Compte | Rôle | Périmètre |
|---|---|---|
| `marwen.b@medicacom.com` | Direction Générale | Organisation |
| `admin.entreprise@medicacom.com` | Administrateur entreprise | Organisation |
| `l.trabelsi@medicacom.com` | Responsable de département | Commercial |
| `h.gharbi@medicacom.com` | Responsable de département | Production |
| `k.zouari@medicacom.com` | DSI / Architecte SI | Organisation |
| `n.hamdi@medicacom.com` | Data Office / Data Engineer | Organisation |
| `y.benali@medicacom.com` | AI Lead / Data Scientist | Organisation |
| `m.dupuis@medicacom.com` | Finance / Contrôle de gestion | Organisation |
| `f.moreau@medicacom.com` | PMO / Chef de projet | Organisation |
| `audit@medicacom.com` | Auditeur / Lecture seule | Organisation |
| `a.rousseau@medicacom.com` | Contributeur métier | R&D |
| `admin@medicacom.com` | Administrateur Medicacom | Plateforme |

Connectez-vous successivement avec plusieurs de ces comptes : le menu, l'écran d'accueil,
les données visibles et les actions proposées changent à chaque fois. Le détail du modèle
de droits est dans [docs/RBAC.md](docs/RBAC.md).

L'écran de connexion propose ces comptes dans un panneau dépliant, alimenté par l'API et
**présent uniquement en développement**. Passer `ENVIRONMENT=production` le fait
disparaître sans toucher au frontend.

---

## Docker

Un `docker-compose.yml` monte PostgreSQL, le backend et le frontend :

```bash
docker compose up --build
```

Au premier démarrage, appliquez les migrations et le seed dans le conteneur backend :

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

Le frontend est alors disponible sur `http://localhost:5173`, l'API sur `http://localhost:8000`.

---

## Les six écrans

L'écran d'accueil dépend des droits : la Direction voit le portefeuille consolidé, un
responsable voit son département, les autres profils sont dirigés vers leur écran de
travail.

| Écran | Chemin | Contenu |
|---|---|---|
| Tableau de bord Direction | `/` | 4 KPI, matrice Impact × Faisabilité, répartition par phase TOGAF, top priorités |
| Tableau de bord Département | `/` | Agrégats bornés au périmètre : opportunités, projets, risques, KPI métier |
| Diagnostic & Readiness | `/diagnostic` | Jauge de readiness, échelle 0→5, barres par dimension, alerte sur les dimensions bloquantes, preuves collectées |
| Opportunités | `/opportunites` | Liste filtrable, alerte doublons, formulaire de recueil sur `/opportunites/nouvelle` |
| Portefeuille IA | `/portefeuille` | Table filtrable par département, type de solution, phase, score et statut ; repriorisation |
| Fiche projet | `/fiches/:id` | Contexte AS-IS, solution recommandée, KPI baseline/cible, business case, risques, score de priorité, décision comité, export |
| Valeur & ROI | `/valeur` | TCO, gains, ROI, payback, gains par département, classement ROI, KPI avant/après |
| Architecture & données | `/architecture` | Processus, applications, sources de données et leur qualité |
| Administration | `/administration` | Organisation, sites, départements, utilisateurs, rôles et permissions |
| Journal d'audit | `/audit` | Historique des modifications, ancienne valeur → nouvelle valeur |

---

## Ce que calcule la plateforme

### Readiness (M2 / M5)

Chaque dimension est notée de 0 à 5, pondérée par son poids et par la confiance
déclarée de la réponse :

```
score global = 100 × Σ(note × poids × confiance) / Σ(5 × poids × confiance)
```

La moyenne affichée par axe est pondérée par le seul poids : elle décrit le niveau
de maturité constaté, pas la solidité du constat. Une dimension sous le seuil de la
campagne est **bloquante** si elle est marquée critique (à remédier avant toute mise
en production), sinon elle est signalée comme **point de vigilance**.

### Qualification de solution (M4)

Un moteur de règles pondérées choisit entre IA classique, computer vision, NLP,
générative, agentique, BI, RPA et amélioration de processus. Chaque type porte des
règles dont certaines sont bloquantes : non satisfaite, une règle bloquante
disqualifie le type. L'API renvoie systématiquement les règles déclenchées, les
alternatives écartées avec leur score, et les garde-fous à mettre en place — un
périmètre GxP ajoute automatiquement les exigences de validation informatique et de
traçabilité ALCOA+.

### Priorisation (M7)

```
score = 0,25 × impact métier    + 0,20 × impact financier + 0,20 × faisabilité
      + 0,15 × alignement       + 0,10 × readiness        + 0,10 × synergies
      − pénalité de risque
```

Le risque brut vaut probabilité (1→5) × impact (1→5), soit 1 à 25 ; la pénalité vaut
`risque / 25 × 15` points. Les poids sont paramétrables par appel et renormalisés à 1
pour rester comparables. `GET /opportunities/{id}/score` renvoie le détail de chaque
contribution.

### Valeur (M10)

```
TCO          = capex + opex annuel × horizon
ROI (%)      = (gains cumulés sur l'horizon − TCO) / TCO × 100
payback      = capex / ((gains annuels − opex annuel) / 12)
```

Le payback porte sur l'investissement initial récupéré par le gain annuel net :
lui faire porter trois années d'opex qui ne sont pas encore engagées le fausserait.

---

## Contrôle d'accès (M1)

Le modèle repose sur trois notions séparées : la **permission** dit ce qui est autorisé,
le **périmètre** dit sur quoi, le **rôle** n'est qu'un paquet nommé de permissions.
Onze rôles fonctionnels, quarante et une permissions granulaires, cinq niveaux de
périmètre. Aucune décision d'autorisation ne s'appuie sur un nom de rôle.

L'écriture ne déborde jamais du périmètre, les listes sont filtrées, et un objet hors
périmètre répond 404 plutôt que 403 pour ne pas confirmer son existence.

Masquer un bouton côté React relève du confort d'usage : chaque endpoint porte sa propre
vérification et répond 403 à un appel direct non autorisé. Le détail complet, matrice
comprise, est dans [docs/RBAC.md](docs/RBAC.md).

## Multi-tenant et audit

Chaque table métier porte `organization_id`. Le jeton JWT transporte l'identifiant du
tenant, et toutes les requêtes le reprennent comme filtre : aucune lecture ni écriture
ne peut sortir de l'organisation de l'utilisateur connecté. Manipuler un identifiant
dans l'URL ne contourne rien.

Toute modification significative alimente `audit_log` (auteur, horodatage, entité,
ancienne valeur → nouvelle valeur, adresse IP). Ce journal est en insertion seule :
l'API n'expose ni mise à jour ni suppression sur cette table.

## Tests

```bash
cd backend && python -m pytest
```

Cent douze tests couvrent l'authentification, les permissions par rôle, le périmètre
départemental, l'isolation multi-tenant, le cycle de vie des opportunités, l'instruction
du diagnostic et trois propriétés structurelles de l'API.

---

## Structure du backend

```
backend/app/
  main.py                 montage des routers, CORS, OpenAPI
  core/                   config (.env), sécurité (JWT, bcrypt), moteur SQLAlchemy
  models/                 organization, rbac, diagnostic, architecture,
                          opportunity, project, value, governance
  schemas/                schémas Pydantic v2 par domaine
  api/deps.py             session, utilisateur courant, RBAC, isolation tenant
  api/routers/            auth, organization, diagnostic, opportunities,
                          crossings, projects, sheets, value, dashboards, admin
  services/               readiness, recommendation, scoring, crossing,
                          value, questionnaire, audit
  seed.py                 jeu de démonstration
```

### Modules couverts

| Module | Router | Objet |
|---|---|---|
| M1 | `auth`, `organization` | Authentification JWT, RBAC granulaire, périmètres, sites, départements, utilisateurs, rôles |
| M2 / M5 | `diagnostic` | Campagnes AS-IS, réponses pondérées, readiness et dimensions bloquantes |
| M3 | `opportunities` | Questionnaire commun et volet départemental, recueil des besoins |
| M4 | `opportunities` | Moteur de qualification explicable |
| M6 | `crossings` | Processus, applications, sources de données, KPI, dépendances, doublons |
| M7 | `opportunities` | Score de priorité, rangs et vagues, poids paramétrables |
| M8 | `sheets` | Génération de la fiche, versions, validation comité, export |
| M9 | `projects` | Phases, jalons, tâches, risques, mitigations, incidents, gates |
| M10 | `value` | Coûts, bénéfices, mesures, business case, ROI portefeuille |
| M11 | `dashboards` | Endpoints d'agrégation des écrans |
| M12 | `admin` | Journal d'audit et notifications |

---

## Jeu de démonstration

Le seed installe un laboratoire à quatre implantations (Tunis, Lyon, Casablanca,
Paris), huit départements, un diagnostic de 14 dimensions et 18 opportunités
couvrant tous les types de solution, avec leurs KPI, business cases, dépendances,
risques et projets. Les chiffres consolidés qui en ressortent :

| Indicateur | Valeur |
|---|---|
| Readiness global | 62 / 100 (niveau 3, opérationnel) |
| Dimensions bloquantes | Gouvernance data (2) et Infrastructure IA (2) |
| Opportunités | 18, réparties 5 / 4 / 3 / 3 / 3 sur le funnel |
| Investissement | 2,4 M€ engagés sur 3,1 M€ budgétés |
| ROI portefeuille | 184 % sur 3 ans, payback moyen 11 mois |

---

## Tests manuels utiles

```bash
# santé de l'API
curl http://127.0.0.1:8000/health

# jeton
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"marwen.b@medicacom.com","password":"medicacom2026"}'

# tableau de bord (remplacez $TOKEN)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/dashboards/direction
```

Vérification des types côté frontend :

```bash
cd frontend && npm run typecheck && npm run build
```
