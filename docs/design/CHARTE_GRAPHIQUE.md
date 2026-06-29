# Charte graphique SUPMEAL

## Identite

- **Nom** : SUPMEAL
- **Slogan** : "Cuisinez, partagez, savourez."
- **Ambiance** : chaleureuse, moderne, gourmande et accessible. Ni trop "food blog lifestyle" ni trop "outil pro froid".

## Palette

### Couleurs principales

| Nom              | Hex       | Usage |
|------------------|-----------|-------|
| Tomato 500       | `#E94B3C` | Couleur primaire : boutons, accents, lien actif |
| Tomato 600       | `#C8392E` | Hover / actif des boutons primaires |
| Tomato 100       | `#FDE2DE` | Fonds sutils, badges chauds |
| Cream 50         | `#FFF8F1` | Fond de page global |
| Cream 100        | `#F6EBDC` | Surface elevee (cartes, modales) |
| Charcoal 900     | `#1F1B16` | Texte principal |
| Charcoal 700     | `#3F3A33` | Texte secondaire |
| Charcoal 500     | `#7A7368` | Texte desactive, placeholders |

### Couleurs d'etat

| Nom       | Hex       | Usage |
|-----------|-----------|-------|
| Success   | `#2E8B57` | Validation |
| Warning   | `#D08C2C` | Avertissement |
| Danger    | `#B33A3A` | Erreur / suppression |
| Info      | `#2C7A7B` | Information |

## Typographie

- **Titres** : `Poppins` (Google Fonts), 600, hierarchie 28 / 22 / 18 / 16.
- **Corps** : `Inter` (Google Fonts), 400/500, taille de base 15px, line-height 1.5.
- **Monospace** (recettes, code) : `JetBrains Mono`, 14px.

## Iconographie

- **Bibliotheque** : `lucide-react` (ligne fine, consistente, MIT).
- **Style** : outline, 1.5px, taille 20-24px en UI, 32px+ pour les illustrations.

## Logo

- Logotype : mot **SUPMEAL** en Poppins 700, couleur Tomato 500.
- Marque : ustensile de cuisine stylise (fouet + toque) au-dessus du mot, en Charcoal 900.
- Declinaisons : couleur, monochrome clair, monochrome sombre.

## Espacement & grille

- **Base** : 4px.
- **Echelle** : 4, 8, 12, 16, 24, 32, 48, 64.
- **Radius** : 8px (boutons), 12px (cartes), 16px (modales).
- **Ombres** : 3 niveaux (subtile, carte, elevee) en tons chauds.

## Composants

- **Boutons** : primaires (Tomato 500), secondaires (Charcoal 900 outline), tertiaires (texte seul).
- **Cartes recette** : image 16:10, titre Poppins 18, meta en Charcoal 500, badge favori en haut a droite.
- **Formulaires** : labels au-dessus, focus ring Tomato 500 a 30% d'opacite.
- **Navigation** : barre laterale 240px en desktop, drawer en mobile.

## Ton & microcopy

- Tutoiement, ton chaleureux, direct.
- Exemples :
  - "Bienvenue, {prenom} ! Qu'est-ce qu'on cuisine aujourd'hui ?"
  - "Recette ajoutee a vos favoris."
  - "Aucun ingredient ne manque. Bonne cuisine !"

## Accessibilite

- Contraste minimum AA (4.5:1) sur tous les textes.
- Focus visible systematiquement.
- Tous les elements interactifs accessibles au clavier.
- Messages d'erreur explicites, annonces pour les actions importantes.