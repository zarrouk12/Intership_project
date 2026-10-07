# Rapport technique — Medicacom AOI Transformation

Source LaTeX du rapport de projet. Tout est écrit en LaTeX pur : les diagrammes
(cas d'utilisation, classes, architecture, flux, sécurité) sont dessinés en TikZ,
aucun outil externe n'est nécessaire pour les produire.

## Arborescence

```
rapport/
  main.tex                     point d'entrée, variables de page de garde
  preambule.tex                packages, couleurs, styles TikZ, macros
  chapitres/
    00-pages-liminaires.tex    couverture, remerciements, résumé, abstract, tables
    01-introduction.tex        introduction générale
    02-analyse.tex             contexte, problématique, objectifs, modules M1–M12
    03-conception.tex          acteurs, rôles, cas d'utilisation, modèle de données
    04-realisation.tex         technologies, moteur de règles, algorithmes, sécurité
    05-interfaces.tex          les 14 écrans + encadrés de présentation orale
    06-tests.tex               stratégie, résultats, difficultés
    07-conclusion.tex          bilan, limites, perspectives
  annexes/
    a-soutenance.tex           guide de démonstration minuté + 30 questions/réponses
    b-references.tex           documentations, normes, référentiels
  images/                      captures d'écran à déposer (voir images/README.md)
```

## Avant de compiler

Ouvrir `main.tex` et renseigner les variables marquées `[À COMPLÉTER : ...]` :
université, école, département, formation, diplôme, auteur, encadrants.
Aucune information d'établissement n'a été inventée.

## Compilation

```bash
cd rapport
latexmk -pdf main.tex
```

ou, sans latexmk :

```bash
pdflatex main.tex
pdflatex main.tex     # deuxième passe : table des matières, figures, références
```

Le moteur attendu est **pdfLaTeX** (`inputenc` en UTF-8 + `fontenc` T1).

### Paquets requis

`geometry`, `babel`, `lmodern`, `microtype`, `amsmath`, `amssymb`, `textcomp`,
`setspace`, `xcolor` (option `table`), `graphicx`, `float`, `tikz`, `pgfplots`,
`booktabs`, `array`, `longtable`, `tabularx`, `multirow`, `makecell`, `enumitem`,
`caption`, `subcaption`, `fancyhdr`, `titlesec`, `framed`, `listings`, `hyperref`,
`cleveref`.

Tous figurent dans une distribution TeX Live complète ou MiKTeX.

## Captures d'écran

Le document compile **sans aucune capture** : chaque emplacement affiche alors un
cadre pointillé nommant le fichier attendu. Voir `images/README.md` pour la liste
des quinze noms de fichiers.
