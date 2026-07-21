# Suggestions de recettes

La page **Suggestions** vous aide a trouver une recette realisable a partir des ingredients
que vous avez deja sous la main.

## Acceder a la page

Dans le menu lateral, cliquez sur l icoine etincelle **Suggestions**. La page est accessible
a tous les utilisateurs connectes (et egalement aux visiteurs anonymes, qui ne verront que
les recettes publiques).

## Saisir les ingredients

1. Tapez un ingredient dans le champ (ex : `tomate`, `oignon`, `ail`).
2. Validez avec **Entree** ou cliquez sur **Ajouter**.
3. Les ingredients apparaissent sous forme de pastilles ; cliquez sur la croix pour en retirer.
4. Optionnel : remplissez les filtres **Temps de preparation max** et **Temps de cuisson max**.

Vous pouvez saisir jusqu a 50 ingredients. La comparaison est **insensible aux accents et a la
casse** (`echalote` matche `échalote`, `CREME  fraiCHE` matche `crème fraîche`).

## Lancer la recherche

Cliquez sur **Trouver des recettes**. Le serveur :

1. Filtre les recettes visibles par vous (personnelles, publiques, ou dans vos cookbooks).
2. Filtre par duree maximale si renseignee.
3. Calcule un score de matching par recette :
   `score = nombre d ingredients detenus / nombre total d ingredients de la recette`.
4. Trie les resultats par score decroissant, puis par nombre d ingredients manquants croissant,
   puis par duree totale croissante.
5. Renvoie les 10 meilleures suggestions (limite ajustable cote serveur).

## Lire un resultat

Chaque suggestion affiche :

- Le titre et la photo de la recette (cliquez pour ouvrir la fiche detaillee).
- Le **pourcentage de matching** :
  - >= 80% : vert (vous avez presque tout).
  - >= 50% : orange (il manque quelques ingredients).
  - sinon : gris (recette incomplete mais realisable).
- La liste des ingredients que vous avez deja (vert).
- La liste des ingredients manquants (orange) pour vous aider a faire vos courses.

## Cas d usage

- **« Qu est-ce que je peux faire avec ce qu il me reste ? »** : saisissez les fonds de
  frigo et laissez le suggester faire.
- **Courses ciblees** : notez les ingredients manquants des recettes qui vous interessent
  pour ne rien oublier au supermarche.
- **Planification rapide** : combinez avec la page Planning pour bloquer un creneau
  directement depuis une recette suggeree.

## Limites connues

- Le matching est realise en **postgreSQL** avec un pre-filtre `ILIKE + unaccent`. Pour un
  corpus tres volumineux (>10 000 recettes par utilisateur), la latence peut augmenter ;
  les index `gin_trgm_ops` sur le titre et `GIN` sur le `tsvector` de recherche ont ete
  concus pour rester reactifs.
- Les suggestions dependent de la **qualite des ingredients renseignes** dans vos recettes.
  Une recette dont l ingredient est saisi en liberte (`3 poignees de trucs`) sera plus
  difficile a matcher qu une recette avec `tomate`, `oignon`, etc.
