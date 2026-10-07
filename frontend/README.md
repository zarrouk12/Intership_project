# Frontend — Medicacom AOI Transformation

React 18, Vite, TypeScript, React Router, TanStack Query, Recharts.

## Installation

```bash
npm install
cp .env.example .env    # facultatif
npm run dev
```

L'application est servie sur `http://localhost:5173`. Le proxy de développement relaie
`/api` vers `http://127.0.0.1:8000` ; changez `VITE_API_TARGET` pour viser un autre
backend, ou `VITE_API_URL` pour appeler directement une API distante sans proxy.

| Commande | Effet |
|---|---|
| `npm run dev` | Serveur de développement avec rechargement à chaud |
| `npm run build` | Vérification des types puis build de production dans `dist/` |
| `npm run preview` | Sert le build de production |
| `npm run typecheck` | Vérification des types seule |

## Design system

Les jetons sont définis une seule fois dans `src/styles/global.css` :

| Rôle | Valeur |
|---|---|
| Fond | `#EDF2EF` |
| Surface | `#FFFFFF` |
| Sidebar | `#10231C` |
| Texte / texte atténué | `#16241E` / `#5E6F67` |
| Bordure | `#E1E8E4` |
| Accent vert / vert foncé | `#157F5C` / `#0F5E44` |
| Teal (données) | `#1C6B7D` |
| Ambre (attention) | `#A66A16` |
| Rouge (risque) | `#B23A3A` |

Titres en Fraunces, corps en IBM Plex Sans, chargés depuis Google Fonts. Rayons de
10 à 16 px, cartes bordées sur fond blanc, aucun dégradé.

### Couleur dans les graphiques

Le vert et le teal de la charte restent en dessous du seuil de séparation chromatique
recommandé pour deux séries adjacentes. La couleur n'est donc jamais le seul porteur
d'identité : la matrice étiquette directement ses bulles principales, la légende est
toujours affichée, et les tableaux reprennent le type de solution en toutes lettres.

## Organisation

```
src/
  api/client.ts      instance axios, injection du jeton, gestion du 401
  api/queries.ts     un hook TanStack Query par ressource
  api/types.ts       types miroir des schémas Pydantic
  lib/auth.tsx       contexte d'authentification et garde de route
  lib/format.ts      formatage français des nombres, montants et libellés métier
  components/        Layout, primitives d'interface, icônes, graphiques
  pages/             un fichier par écran
  styles/global.css  jetons et styles de l'application
```

## Authentification

Le jeton JWT est conservé dans `localStorage` sous la clé `medicacom.token`, injecté
par un intercepteur axios. Toute réponse 401 purge le jeton et renvoie vers l'écran de
connexion en mémorisant la page demandée. Les accès en écriture de l'interface suivent
les permissions renvoyées par `/auth/me`, elles-mêmes revérifiées côté API.

## Export de la fiche projet

L'export passe par le client authentifié puis ouvre un blob : le jeton ne transite
jamais par l'URL. La page obtenue est mise en page pour l'impression, ce qui permet de
produire un PDF depuis le navigateur.
