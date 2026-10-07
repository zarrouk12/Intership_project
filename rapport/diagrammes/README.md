# Diagrammes PlantUML

Deux diagrammes, chacun en **version simplifiée** (pour la soutenance et le rapport) et
en **version détaillée** (pour justifier un point précis si le jury creuse).

| Fichier | Contenu | Quand l'utiliser |
|---|---|---|
| [diagramme-classes.puml](diagramme-classes.puml) | 30 entités, 5 attributs en moyenne, 27 associations colorées | **Par défaut** — c'est celui à projeter |
| [diagramme-classes-detaille.puml](diagramme-classes-detaille.puml) | 34 classes (dont les 4 tables d'association), tous les attributs, toutes les clés étrangères | En annexe, ou si on vous demande une colonne précise |
| [diagramme-cas-utilisation.puml](diagramme-cas-utilisation.puml) | 9 acteurs, 24 cas d'utilisation, 7 étapes du parcours | **Par défaut** |
| [diagramme-cas-utilisation-detaille.puml](diagramme-cas-utilisation-detaille.puml) | 12 acteurs, 48 cas d'utilisation, 11 modules | Si on vous interroge sur un module précis |

Les quatre sont dérivés du code réel : attributs issus de `backend/app/models/`,
acteurs issus des 11 rôles de `backend/app/core/rbac.py`, cas d'utilisation
correspondant à des endpoints ou des écrans qui existent.

## Ce qui a été simplifié

**Diagramme de classes.** Trois allègements, sans rien retirer d'essentiel :

1. **Les clés étrangères ne sont plus listées en attributs.** Elles sont portées par les
   associations, ce qui supprime une soixantaine de lignes de texte redondantes.
2. **Les 4 tables d'association disparaissent** en tant que classes. `user_role`,
   `user_department`, `user_site` et `role_permission` deviennent 4 liens
   plusieurs-à-plusieurs directs, au lieu de 4 boîtes et 8 liens.
3. **`Organization` n'est plus relié qu'à ses 4 enfants structurels** (Site, Department,
   User, Role). Les 8 autres liens `Organization → …` ne disaient rien que la note ne
   dise mieux : *toute table métier porte `organization_id`*.

**Diagramme de cas d'utilisation.** 48 cas ramenés à 24, regroupés par étape du parcours
plutôt que par module, et 11 acteurs ramenés à 9 : DSI et Data Office sont fusionnés en
un acteur, et l'Administrateur Medicacom est renvoyé en légende parce qu'il porte les
41 permissions et aurait été relié à tout.

## Ce qui rend les lignes lisibles

Chaque association porte une couleur et une épaisseur (`thickness=2`, `thickness=3` pour
les deux relations structurantes) :

| Couleur | Diagramme de classes | Diagramme de cas d'utilisation |
|---|---|---|
| Vert foncé `#0F5E44` | Organisation et droits (M1) | Administrateur entreprise |
| Vert `#157F5C` | Diagnostic et opportunités (M2–M7) | Responsable de département |
| Teal `#1C6B7D` | Référentiel AS-IS et valeur (M6, M10) | DSI / Data Office |
| Ambre `#A66A16` | Cycle de vie des projets (M9) | Direction Générale |
| Gris `#5E6F67` | Gouvernance documentaire (M8, M12) | — |
| Rouge `#B23A3A` | — | Auditeur, en **pointillés** (lecture seule) |

Une légende est intégrée en bas de chaque diagramme : pas besoin de se souvenir du code
couleur pendant la soutenance.

## Rendu

### En ligne de commande

Nécessite Java, [plantuml.jar](https://plantuml.com/download) et
[Graphviz](https://graphviz.org/download/) (`dot`).

```bash
java -jar plantuml.jar -tsvg diagramme-classes.puml
java -jar plantuml.jar -tsvg diagramme-cas-utilisation.puml

# pour l'insertion dans le rapport LaTeX
java -jar plantuml.jar -tpdf diagramme-classes.puml
```

### Sans rien installer

Coller le fichier sur [plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml/),
ou utiliser l'extension **PlantUML** de VS Code (aperçu par `Alt+D`).

### Si Graphviz n'est pas installé

Ajouter cette ligne juste après `@startuml` :

```
!pragma layout smetana
```

Le moteur interne de PlantUML prend le relais. Le rendu est un peu moins soigné, et
`skinparam linetype ortho` peut alors donner des coudes bizarres — commentez cette ligne
si c'est le cas.

## Insertion dans le rapport LaTeX

Le rapport contient déjà des versions TikZ de ces diagrammes, qui compilent sans outil
externe. Pour utiliser plutôt les rendus PlantUML :

```latex
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{diagrammes/diagramme-classes.pdf}
\caption{Diagramme de classes général}
\label{fig:classes-plantuml}
\end{figure}
```

Préférez le **PDF ou le SVG** au PNG : le diagramme de classes reste lisible au zoom.

## Conventions

- `*--` composition · `o--` agrégation · `--` association
- `<<PK>>` clé primaire · `<<FK>>` clé étrangère (version détaillée uniquement)
- Les colonnes `created_at` et `updated_at`, présentes sur toutes les tables, sont
  omises partout.
- `AuditLog` n'est relié à rien : c'est voulu, la table n'a aucune clé étrangère pour
  qu'une trace survive à la suppression de l'entité qu'elle décrit.
