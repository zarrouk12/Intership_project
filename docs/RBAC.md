# M1 — Modèle RBAC, périmètres et comptes de démonstration

Ce document décrit le contrôle d'accès de la plateforme : les trois notions du modèle,
la matrice rôle × permission, les comptes de test et les commandes utiles.

---

## 1. Le modèle en trois notions

Le système repose sur trois notions distinctes, volontairement séparées :

| Notion | Ce qu'elle exprime | Où elle vit |
|---|---|---|
| **Permission** | Ce qui est autorisé — créer une opportunité, valider une gate | `permission`, catalogue dans [`app/core/rbac.py`](../backend/app/core/rbac.py) |
| **Périmètre** | Sur quoi — plateforme, organisation, site, département, contributions | `role.scope_level`, `user_department`, `user_site` |
| **Rôle** | Un paquet nommé de permissions, assorti d'un périmètre par défaut | `role`, `role_permission`, `user_role` |

```
User ──< user_role >── Role ──< role_permission >── Permission
  │
  ├──< user_department >── Department
  └──< user_site       >── Site
```

Un utilisateur peut porter **plusieurs rôles**. Ses permissions sont l'union de celles de
ses rôles ; son périmètre effectif est **le plus large** de ceux de ses rôles. Un
responsable qui reçoit en plus un rôle transverse voit donc son périmètre s'élargir,
jamais se réduire.

### Ce qui n'est jamais fait

Aucune décision d'autorisation ne s'appuie sur un nom de rôle. On ne trouve nulle part
dans le code :

```python
if user.role == "admin":        # jamais
```

Les endpoints déclarent la permission qu'ils exigent :

```python
@router.post("/users", ...)
def create_user(..., current_user: User = Depends(require_permission("user.create"))):
```

---

## 2. Les cinq niveaux de périmètre

| Niveau | Portée | Rôles concernés |
|---|---|---|
| `platform` | Toutes les organisations clientes | Administrateur Medicacom |
| `organization` | Une organisation entière | Admin entreprise, Direction, DSI, Data Office, AI Lead, Finance, PMO, Auditeur |
| `site` | Les sites de rattachement | Disponible pour les rôles personnalisés |
| `department` | Les départements de rattachement | Responsable de département |
| `own` | Les objets dont l'utilisateur est contributeur | Contributeur métier |

### Lecture et écriture ne suivent pas la même règle

- **Écriture** : elle ne déborde jamais du périmètre. Un responsable Commercial reçoit
  403 s'il tente de créer ou modifier une opportunité de Production.
- **Lecture des listes** : elle est filtrée par le périmètre. Le même responsable voit
  3 opportunités là où la Direction en voit 19.
- **Lecture d'un objet hors périmètre** : elle répond **404**, pas 403. Un 403
  confirmerait l'existence de l'objet à quelqu'un qui n'a pas à la connaître.
- **Vues transverses** : les dépendances interservices et le graphe de croisement
  restent ouverts à qui détient la permission correspondante. Le périmètre borne ce que
  l'on modifie, il n'empêche pas la collaboration.

Ces règles vivent dans `AccessScope` ([`app/api/deps.py`](../backend/app/api/deps.py)).

---

## 3. Matrice rôle × permission

Onze rôles, quarante et une permissions.

| Rôle | Périmètre | Permissions | Rôle de plateforme |
|---|---|---|---|
| Administrateur Medicacom | plateforme | 41 | oui |
| Administrateur entreprise | organisation | 23 | non |
| Direction Générale | organisation | 22 | non |
| Responsable de département | département | 18 | non |
| DSI / Architecte SI | organisation | 16 | non |
| AI Lead / Data Scientist | organisation | 16 | non |
| Auditeur / Lecture seule | organisation | 16 | non |
| Finance / Contrôle de gestion | organisation | 15 | non |
| PMO / Chef de projet | organisation | 15 | non |
| Data Office / Data Engineer | organisation | 14 | non |
| Contributeur métier | contributions | 11 | non |

### Détail par domaine

Légende : **É** écriture, **L** lecture seule, **—** aucun accès.

| Domaine | Admin Medicacom | Admin entr. | Direction | Resp. dépt | Contributeur | DSI | Data Office | AI Lead | Finance | PMO | Auditeur |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Organisation, sites, départements | É | É | L | L | L | L | L | L | L | L | L |
| Utilisateurs et rôles | É | É | L | — | — | — | — | — | — | — | L |
| Diagnostic | É | L | L | É | É | É | É | L | L | L | L |
| Opportunités | É | L | L + validation | É | Création | Modification | L | Modification | L | L | L |
| Recommandation IA | É | L | L | L | L | L | L | **Amendement** | L | L | L |
| Architecture applicative | É | L | L | L | L | **É** | L | L | L | L | L |
| Sources de données | É | L | L | L | L | L | **É** | L | L | L | L |
| Portefeuille | É | L | L + priorisation | L | — | L | L | L | L | L | L |
| Fiche projet | É | L | L + décision | É | L | L | L | É | L | É | L |
| Projets | É | L | L + gates | L | L | L + gates | L | L + gates | L | **É** | L |
| Valeur et P&L | É | L | L + validation | L | — | — | — | — | **É** | L | L |
| Journal d'audit | L | L | L | — | — | — | — | — | — | — | L |

La matrice exhaustive, permission par permission, est produite par
`app.core.rbac.role_matrix()` et vérifiée par les tests.

### Séparations volontaires

Certaines frontières méritent d'être explicites, car elles répondent à des exigences
métier plutôt qu'à une commodité technique :

- **Finance ne touche ni la recommandation IA ni l'architecture.** Elle instruit la
  valeur, pas le choix technique. Un appel à `POST /opportunities/{id}/qualify` par un
  compte Finance répond 403.
- **L'AI Lead n'administre pas les comptes.** Il peut amender une recommandation avec
  justification, pas gérer les utilisateurs.
- **La Direction n'administre pas les utilisateurs.** Elle arbitre et décide.
- **L'auditeur ne peut rien écrire.** Aucune création, modification, suppression ni
  validation, quel que soit le module.
- **L'administrateur d'entreprise ne peut pas s'échapper de son tenant.** Il ne peut ni
  s'attribuer le rôle `admin_medicacom`, ni placer `platform.admin` dans un rôle qu'il
  crée, ni modifier un rôle système.

---

## 4. Isolation multi-tenant

Chaque table métier porte `organization_id`. Le jeton JWT transporte l'identifiant du
tenant, et `get_tenant_id` le lit **depuis le jeton, jamais depuis la requête**.

`get_or_404` vérifie l'appartenance de chaque entité avant de la renvoyer. Concrètement,
connaître l'identifiant d'une ressource d'une autre organisation ne sert à rien :

```
GET    /api/v1/opportunities/{id_d_un_autre_tenant}   → 404
PATCH  /api/v1/opportunities/{id_d_un_autre_tenant}   → 404
DELETE /api/v1/opportunities/{id_d_un_autre_tenant}   → 404
POST   /api/v1/org/users  avec un department_id étranger → 404
POST   /api/v1/org/users  avec un role_code étranger     → 422
```

Neuf tests couvrent ces cas dans
[`tests/test_tenant_isolation.py`](../backend/tests/test_tenant_isolation.py).

---

## 5. Comptes de démonstration

Mot de passe commun : `medicacom2026`.

| Compte | Rôle | Périmètre | Atterrit sur |
|---|---|---|---|
| `admin@medicacom.com` | Administrateur Medicacom | Plateforme | Tableau de bord Direction |
| `admin.entreprise@medicacom.com` | Administrateur entreprise | Organisation | Administration |
| `marwen.b@medicacom.com` | Direction Générale | Organisation | Tableau de bord Direction |
| `l.trabelsi@medicacom.com` | Responsable de département | Commercial | Tableau de bord Département |
| `h.gharbi@medicacom.com` | Responsable de département | Production | Tableau de bord Département |
| `c.lambert@medicacom.com` | Responsable de département | Affaires réglementaires | Tableau de bord Département |
| `a.rousseau@medicacom.com` | Contributeur métier | R&D | Opportunités |
| `k.zouari@medicacom.com` | DSI / Architecte SI | Organisation | Tableau de bord Département |
| `n.hamdi@medicacom.com` | Data Office / Data Engineer | Organisation | Tableau de bord Département |
| `y.benali@medicacom.com` | AI Lead / Data Scientist | Organisation | Tableau de bord Département |
| `m.dupuis@medicacom.com` | Finance / Contrôle de gestion | Organisation | Tableau de bord Département |
| `f.moreau@medicacom.com` | PMO / Chef de projet | Organisation | Tableau de bord Département |
| `audit@medicacom.com` | Auditeur / Lecture seule | Organisation | Tableau de bord Département |

Ces comptes n'existent que pour le développement et la démonstration. Le mot de passe est
défini dans le seed, jamais dans le code applicatif.

---

## 6. Ce que voit chaque rôle

La navigation est construite à partir des permissions renvoyées par `/auth/me` : une
entrée de menu n'apparaît que si son écran est réellement accessible.

| Rôle | Entrées de menu |
|---|---|
| Direction | Tableau de bord, Diagnostic, Opportunités, Portefeuille, Fiches projet, Valeur & ROI, Administration, Audit |
| Admin entreprise | Diagnostic, Opportunités, Portefeuille, Fiches projet, Valeur & ROI, Administration, Audit |
| Responsable dépt | Tableau de bord, Diagnostic, Opportunités, Portefeuille, Fiches projet, Valeur & ROI |
| DSI / Data Office | Tableau de bord, Diagnostic, Opportunités, **Architecture & données**, Portefeuille, Fiches projet |
| Finance / PMO | Tableau de bord, Diagnostic, Opportunités, Portefeuille, Fiches projet, Valeur & ROI |
| Auditeur | Comme la Direction, mais aucun bouton d'action |
| Contributeur | Diagnostic, Opportunités, Fiches projet |

Les actions suivent la même règle. Par exemple, « Nouvelle opportunité » n'apparaît que
pour qui détient `opportunity.create`, « Recalculer la priorisation » que pour
`portfolio.prioritize`, et le bloc « Décision comité » de la fiche projet que pour
`sheet.approve`.

**Masquer un bouton n'est pas une protection.** C'est un confort d'usage. Un appel direct
à l'API sans la permission reçoit 403 dans tous les cas.

---

## 7. Journal d'audit

Chaque action significative alimente `audit_log` en insertion seule : l'API n'expose ni
mise à jour ni suppression sur cette table.

Sont tracés : création et modification d'utilisateur, ajout ou retrait de rôle,
changement de département ou de site, activation et désactivation, création et
modification de rôle, connexion, changement de mot de passe, et toutes les modifications
métier des modules M2 à M12.

Chaque entrée conserve l'auteur, l'horodatage, l'organisation, l'entité visée, l'adresse
IP quand elle est disponible, et le couple ancienne valeur → nouvelle valeur limité aux
champs réellement modifiés. Une requête qui ne change rien n'écrit pas de ligne.

L'écran `/audit` restitue ce journal avec un rendu lisible du delta.

---

## 8. Instruction du diagnostic

L'action « Poursuivre le diagnostic » ouvre le questionnaire de la campagne. Chaque
dimension y porte sa note de 0 à 5, son poids, sa confiance et sa preuve. Seules les
lignes réellement modifiées partent au backend, via `PATCH /diagnostic/responses/{id}`.

Une règle gouverne ce calcul : **une confiance nulle signifie « dimension non encore
instruite »**. Une telle dimension sort du score et des moyennes d'axe, au lieu de
compter comme un zéro, et fait baisser le taux de complétion. Sans cette règle, ouvrir
une nouvelle dimension dans le référentiel ferait mécaniquement chuter le readiness de
toutes les campagnes.

Le taux de complétion est donc **calculé**, jamais saisi :

```
complétion = dimensions instruites / dimensions totales
```

Les rôles portant `diagnostic.answer` — responsable de département, contributeur métier,
DSI, Data Office — renseignent le questionnaire. Les autres l'ouvrent en consultation :
le bouton devient « Voir le questionnaire », les champs sont désactivés et le bouton
d'enregistrement disparaît. La Direction et l'administrateur d'entreprise sont dans ce
cas : ils consultent le diagnostic, ils ne le remplissent pas.

Le bouton « Exporter » produit un CSV séparé par points-virgules, avec BOM UTF-8, qui
s'ouvre directement dans Excel en locale française. Il contient une ligne par dimension
avec son état, suivie d'un bloc de synthèse.

---

## 9. Opportunités : cycle de vie et priorisation

### CRUD complet

| Action | Endpoint | Permission | Écran |
|---|---|---|---|
| Lister | `GET /opportunities` | `opportunity.read` | Opportunités, Portefeuille |
| Consulter | `GET /opportunities/{id}` | `opportunity.read` | Fiche projet |
| Créer | `POST /opportunities` | `opportunity.create` | Nouvelle opportunité |
| Modifier | `PATCH /opportunities/{id}` | `opportunity.update` | Modifier l'opportunité |
| Supprimer | `DELETE /opportunities/{id}` | `opportunity.update` | Liste et formulaire, avec confirmation |

Le formulaire de modification est pré-rempli depuis l'API et **n'envoie que les champs
réellement changés**. Le journal d'audit reste ainsi lisible : une ligne par champ
modifié, au lieu d'un enregistrement complet à chaque sauvegarde. Le bouton reste
désactivé tant que rien n'a bougé, et l'écran affiche le nombre de champs concernés.

Créer ou modifier relance la qualification et le score : changer les réponses fait
changer le type de solution recommandé. C'est vérifié par les tests — passer d'un besoin
de prédiction à un besoin de rédaction fait passer la recommandation de « IA classique »
à « Générative ».

La suppression demande une confirmation nommant l'opportunité et ce qui disparaît avec
elle, puis est tracée dans le journal d'audit.

### Priorisation pondérée

Le bouton « Recalculer la priorisation » ouvre un panneau qui expose les six critères du
score. Les poids sont réglables, renormalisés à 100 % à l'affichage comme côté serveur,
et le panneau affiche ensuite les mouvements de rang réellement produits.

Auparavant le bouton envoyait toujours les poids par défaut : le classement ne pouvait
donc jamais changer, et l'action paraissait sans effet. Rendre les pondérations
réglables est ce qui lui donne un sens, conformément à l'exigence M7 de poids
paramétrables.

Le panneau permet aussi d'ajuster la taille de vague et de recalculer le critère de
synergie depuis le graphe de dépendances. Cette dernière option reste désactivée par
défaut : elle écrase les valeurs évaluées en atelier, ce qui doit rester un acte
explicite.

---

## 10. Commandes

Ces commandes supposent l'environnement virtuel activé. Sous PowerShell :
`.\.venv\Scripts\Activate.ps1` — voir le [README backend](../backend/README.md) pour
les autres terminaux.

```bash
cd backend

# Migrations
alembic upgrade head
alembic downgrade -1

# Données de démonstration (11 rôles, 13 comptes)
python -m app.seed --reset

# Tests
python -m pytest                                   # les 93 tests
python -m pytest tests/test_permissions.py      -v # droits par rôle
python -m pytest tests/test_scope.py            -v # périmètre départemental
python -m pytest tests/test_tenant_isolation.py -v # cloisonnement des organisations
python -m pytest tests/test_opportunities.py    -v # CRUD et priorisation
python -m pytest tests/test_diagnostic.py       -v # instruction du diagnostic
python -m pytest tests/test_endpoint_protection.py -v # garde-fous structurels
```

Les tests s'exécutent contre la base de développement peuplée par le seed. Ils créent
une seconde organisation temporaire pour éprouver l'isolation, puis la suppriment ; ils
nettoient chaque objet qu'ils créent. Le jeu de démonstration n'est pas altéré.

### Garde-fous automatisés

[`tests/test_endpoint_protection.py`](../backend/tests/test_endpoint_protection.py)
vérifie trois propriétés structurelles de l'API, indépendamment du métier :

1. Aucune route n'est exposée sans contrôle de permission, hors une liste explicite
   d'endpoints ouverts (connexion, profil propre, notifications propres).
2. Aucune dépendance n'est traitée comme un paramètre de requête. Ce cas s'est produit
   pendant le développement : une annotation `Scope` non importée dans un router avait
   été interprétée par FastAPI comme un `?scope=`, rendant l'endpoint inutilisable sans
   lever d'erreur.
3. Aucune dépendance n'est traitée comme un corps de requête.
