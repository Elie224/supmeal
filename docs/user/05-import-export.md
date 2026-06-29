# Importer et exporter

SUPMEAL vous permet de recuperer vos donnees a tout moment et d en importer depuis d autres applications.

## Exporter mes donnees

1. Allez dans **Parametres** > **Donnees**.
2. Cliquez sur **Exporter JSON** ou **Exporter CSV** :
   - **JSON** : export complet (recettes personnelles + cookbooks, avec ingredients, etapes, tags, membres).
   - **CSV** : export tabulaire (une ligne par ingredient/etape par recette).
3. Un fichier est telecharge sur votre ordinateur.

**Important** : les fichiers exportes contiennent vos donnees **en clair**. Ne les partagez pas publiquement.

## Importer des donnees

1. Dans **Parametres** > **Donnees** > **Importer**, choisissez le type de fichier (JSON ou CSV).
2. Selectionnez le fichier sur votre ordinateur.
3. SUPMEAL cree automatiquement les recettes (et cookbooks pour le JSON) et vous en attribue la paternite.

## Format Mealie

SUPMEAL supporte l import au **format Mealie** (JSON). Si vous migrez depuis Mealie :

1. Dans Mealie, exportez vos recettes (format JSON).
2. Dans SUPMEAL, importez ce fichier via le bouton JSON.
3. Vos recettes sont converties et ajoutees a votre compte.

## Format CSV

Le CSV suit la structure suivante (1 ligne par ingredient OU par etape) :

```
title,description,servings,prep_time,cook_time,ingredient,quantity,unit,step,tags,source
Tarte tatin,"Classique",6,20,45,pommes,6,,,
,,,,sucre,200,g,,
,,,,beurre,100,g,,
,,,,,,,1,Prechauffer le four a 180,
```

Vous pouvez exporter un modele depuis SUPMEAL pour voir un exemple.