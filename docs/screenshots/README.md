# Captures d ecran

Ce dossier heberge les captures d ecran destinees au rendu final.

> Les images doivent etre ajoutees **apres deploiement** (elles dependent des donnees
> reelles affichees par l application). Chaque fichier est reference par son nom dans
> les sections ci-dessous.

## Captures obligatoires (parcours utilisateur)

| Fichier cible | Parcours | Description |
|---|---|---|
| `01-login.png` | Inscription / connexion | Page de login avec les boutons OAuth Google + GitHub visibles. |
| `02-dashboard.png` | Tableau de bord | Liste des recettes personnelles avec filtres visibles. |
| `03-recipe-detail.png` | Detail recette | Ingredients structures, etapes, image, tags. |
| `04-cookbooks.png` | Liste des cookbooks | Cartes de cookbooks avec roles par membre. |
| `05-cookbook-chat.png` | Chat cookbook | Discussion temps reel entre plusieurs membres. |
| `06-meal-plan.png` | Planning | Vue hebdomadaire avec repas planifies. |
| `07-shopping-list.png` | Liste de courses | Liste generee a partir du planning. |
| `08-suggestions.png` | Suggestions | Resultats avec pourcentage de matching et ingredients manquants. |
| `09-admin.png` | Administration | Stats globales + moderation recettes. |

## Captures bonus (valorisees au rendu)

| Fichier cible | Parcours | Description |
|---|---|---|
| `10-import.png` | Import | Boite de dialogue d import JSON/CSV. |
| `11-export.png` | Export | Telechargement d un export JSON ou CSV. |
| `12-mobile.png` | Mobile | Meme ecran sur smartphone (PWA / responsive). |

## Comment generer les captures

1. Lancer la stack en local : `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`.
2. Ouvrir http://localhost:5173 dans le navigateur.
3. Creer des donnees de demonstration (`make seed` ou `test-data/import/supmeal_import_test.json`).
4. Utiliser l outil de capture natif (Win+Shift+S sous Windows, ou un outil dedie comme ShareX).
5. Sauvegarder chaque capture dans ce dossier en respectant la nomenclature ci-dessus.
6. Referencer ensuite les fichiers dans le manuel utilisateur (`docs/user/*.md`) avec une
   ligne `![Legende](./screenshots/01-login.png)` apres chaque section de feature.

## Outils recommandes

- **ShareX** (Windows, gratuit) : capture, annotation, redimensionnement automatises.
- **Flameshot** (Linux, open source) : capture + annotation directement dans l UI.
- **Shottr** (macOS) : leger, support PNG/JPG, redimensionnement rapide.

Toutes les images doivent etre :

- En format PNG (preserver la netete des ecrans Retina).
- D une largeur maximale de 1280 px (eviter les fichiers trop lourds dans le PDF de rendu).
- Annotees (flèches, zones surlignees) si elles illustrent une fonctionnalite precise.
