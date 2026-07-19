# Maquettes textuelles des ecrans cles

## 1. Auth - Connexion

```
+------------------------------------------------------+
|                                                      |
|                                                      |
|                       SUPMEAL                        |
|              Cuisinez, partagez, savourez.           |
|                                                      |
|   +----------------------------------------------+   |
|   | Email                                        |   |
|   | [____________________________]               |   |
|   |                                              |   |
|   | Mot de passe                                 |   |
|   | [____________________________]  [oeil]       |   |
|   |                                              |   |
|   | [   Se connecter   ]                         |   |
|   |                                              |   |
|   | -- ou continuer avec --                      |   |
|   | [G  Google] [GH  GitHub]                     |   |
|   |                                              |   |
|   | Pas encore de compte ? Creer un compte       |   |
|   | Mot de passe oublie ?                        |   |
|   +----------------------------------------------+   |
|                                                      |
+------------------------------------------------------+
```

## 2. Dashboard

```
+----------------+----------------------------------------+
| [Logo] SUPMEAL | Bonjour, Marie  [+ Nouvelle recette]  |
|                | ----------------------------------------|
|  Tableau de    | [ Recherche : titre, ingredient... ]  |
|  bord          |                                        |
|                | [Tous] [Favoris] [Recents] [Plannif]  |
|  Mes recettes  |                                        |
|  Mes cookbooks |  +-----------+  +-----------+         |
|  Planning      |  | [img]     |  | [img]     |         |
|  Import/Export |  | Tarte...  |  | Risotto...|         |
|  Parametres    |  | 45min  4p |  | 30min  2p |         |
|                |  +-----------+  +-----------+         |
|  + Creer un    |                                        |
|    cookbook    |  Cookbooks partages                    |
|                |  +-----------+  +-----------+         |
|                |  | Famille   |  | Colocs    |         |
|                |  | 12 rec.   |  | 8 rec.    |         |
|                |  +-----------+  +-----------+         |
+----------------+----------------------------------------+
```

## 3. Page recette (detail)

```
+------------------------------------------------------+
| < Retour    [Favori] [Planifier] [Editer] [Supprimer] |
|                                                      |
|  +----------------+   Tarte tatin                     |
|  |                |   ★★★★☆ (4.2) - 18 avis          |
|  |   [image]      |                                    |
|  |                |   Prep 20min | Cuisson 45min      |
|  +----------------+   6 portions | Dessert            |
|                                                      |
|  --- Ingrédients ---        --- Etapes ---          |
|  - 6 pommes           1. Prechauffer le four a 180. |
|  - 200g sucre         2. Couper les pommes...        |
|  - 100g beurre        3. ...                          |
|  - 1 pate feulletee                                    |
|                                                      |
|  --- Commentaires (cookbook) ---                     |
|  [Avatar] Lucas : J'ai ajoute une lichette de canelle |
|  [Ecrire un commentaire.............] [Envoyer]      |
|                                                      |
+------------------------------------------------------+
```

## 4. Cookbook partage

```
+------------------------------------------------------+
| < Mes cookbooks    Cookbook : "Famille"              |
|                                                      |
| [Recettes] [Membres] [Discussion] [Parametres]       |
|                                                      |
| [Recherche dans le cookbook.............]            |
| [Filtres : tags, temps, ingredients, favoris]        |
|                                                      |
| Membres : Marie (Createur) | Lucas (Editeur)         |
|           Sophie (Lecteur) | Paul (Commentateur)     |
|                                                      |
| +-----------+  +-----------+  +-----------+          |
| | Tarte...  |  | Gratin... |  | Soupe...  |          |
| | 45min     |  | 1h        |  | 30min     |          |
| +-----------+  +-----------+  +-----------+          |
+------------------------------------------------------+
```

## 5. Planning de repas

```
+------------------------------------------------------+
| < Tableau de bord     Planning de la semaine         |
|                                                      |
|  < Semaine du 23 juin >                              |
|                                                      |
|   Lun     Mar     Mer     Jeu     Ven     Sam     Dim|
|  +------+ +------+ +------+ +------+ +------+ +------+|
|  | midi | | midi | | midi | | midi | | midi | | midi ||
|  | Tarte| |      | | Risot| |      | |      | |      ||
|  +------+ +------+ +------+ +------+ +------+ +------+|
|  | soir | | soir | | soir | | soir | | soir | | soir ||
|  | Soupe| | Tarte| |      | | Gratin| |      | |      ||
|  +------+ +------+ +------+ +------+ +------+ +------+|
|                                                      |
|  Bouton : [ Generer la liste de courses ]            |
+------------------------------------------------------+
```

## 6. Parametres utilisateur

```
+------------------------------------------------------+
| < Parametres                                         |
|                                                      |
|  --- Profil ---                                      |
|  Nom         [_______________]                        |
|  Email       [_______________] (verifie)              |
|  Avatar      [Choisir une image]                     |
|                                                      |
|  --- Securite ---                                    |
|  Mot de passe   [Changer le mot de passe]            |
|  Connexions     Google [Connecter]                    |
|                 GitHub [Connecter]                    |
|                                                      |
|  --- Preferences culinaires ---                      |
|  Regime        [Aucun v]                             |
|  Allergies     [Gluten, Lactose (chips)]             |
|  Portions def. [4]                                   |
|  Type cuisine  [Francaise, Italienne (chips)]         |
|                                                      |
|  --- Donnees ---                                     |
|  [ Exporter mes donnees (JSON/CSV/Mealie) ]          |
|  [ Importer un fichier ]                             |
+------------------------------------------------------+
```