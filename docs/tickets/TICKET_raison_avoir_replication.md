# Ticket : Replication dynamique de la colonne `Raison de l'avoir`

> Source : `C:\Users\KOURO\Desktop\metabase\avoirs raisons.xls`
> Format source : `.xls` (Excel 97-2003, BIFF8)
> Feuille : `Sheet` (unique)
> Ticket : `[raison-avoir] replication dynamique`

---

## 1. Contexte

Le fichier `avoirs raisons.xls` exporte la liste des avoirs (notes de credit) emis
par SUPMEAL. Une colonne metier doit etre repliquee vers une cible analytique
(Metabase / dataset `ebp_compta` / PostgreSQL) pour exploitation BI.

Le but de ce ticket est de **repliquer la colonne `Raison de l'avoir` du fichier
source vers la cible de maniere dynamique** -- c-a-d que la cible doit
toujours refleter la valeur courante du fichier source, jamais figee a un instant T.

---

## 2. Analyse du fichier source

### 2.1 Structure globale

- Onglet : `Sheet` (unique)
- Dimensions : **338 lignes x 16 colonnes** (1 ligne d'entete + 337 lignes de donnees)
- Plage utilisee : `A1:P337`
- Encodage : texte (`type=1`) partout dans la colonne cible
- Numero document unique absent pour la derniere ligne (sentinelle / fin de fichier)

### 2.2 Entetes (ligne 1)

| Col | En-tete |
|-----|---------|
| A | Numero du document |
| B | Date |
| C | Code Affaire |
| D | Nom du client |
| E | Net a payer |
| F | Net a payer en devise |
| G | Code ISO devise |
| H | Imprime |
| I | Depot |
| J | Multi depots |
| K | Total Net HT |
| L | Utilisateur de creation |
| M | Utilisateur de modification |
| N | Etat |
| O | Etat de validation |
| **P** | **Raison de l'avoir** (colonne a repliquer) |

### 2.3 Distribution de la colonne `P - Raison de l'avoir`

| Valeur | Occurrences | % |
|--------|------------:|--:|
| *(vide)* | 80 | 23.7 % |
| `PRIX` | 68 | 20.2 % |
| `QUANTITE` | 64 | 19.0 % |
| `QUALITE PRODUIT` | 54 | 16.0 % |
| `BUDGET MARKETING` | 26 | 7.7 % |
| `CASSE TRANSPORT` | 22 | 6.5 % |
| `ERREUR DE  PREPARATION` (double espace) | 11 | 3.3 % |
| `DLC` | 10 | 3.0 % |
| `ETIQUETAGE` | 2 | 0.6 % |

8 valeurs distinctes (hors vide) -- vocabulaire controle / liste deroulante cote ERP.

### 2.4 Qualite de la donnee observee

- Depot : 100 % des lignes sur `SOGARIS` (le seul depot du fichier).
- Etat de validation : `Transfere en comptabilite` x333, `En cours de redaction` x3, vide x1.
- Cle de jointure probable : `Numero du document` (cle `AV000xxxxx` / `TMP000xxxxx`).
- **Typo a corriger** : `ERREUR DE  PREPARATION` (double espace) -- normaliser en `ERREUR DE PREPARATION` lors de la copie.
- 80 lignes n'ont pas de raison assignee (a voir si c'est attendu ou si c'est un manque metier).

---

## 3. Objectif

Mettre en place la **replication dynamique** de la colonne `Raison de l'avoir`
depuis `avoirs raisons.xls` vers la cible, **sans figer les valeurs** :

- chaque execution lit la version courante du fichier source ;
- la cible est mise a jour en fonction d'une cle stable (`Numero du document`) ;
- un changement de valeur dans la source se propage automatiquement a la cible ;
- les anciens enregistrements ne sont pas perdus si leur identifiant source disparait
  (strategie `merge` sur la cle, pas `replace` integral).

### Hors-scope (non livre dans ce ticket)

- Modification du vocabulaire metier (liste deroulante cote ERP).
- Correction des 80 lignes vides a la source.
- Replication des autres colonnes (Numero, Date, Code Affaire, etc.) -- ticket distinct si besoin.

---

## 4. Specification fonctionnelle

### 4.1 Cle de replication

- Cle metier : `Numero du document` (colonne A).
- Cle technique cible : `numero_document` (cle primaire / cle de merge).

### 4.2 Strategie de mise a jour

- **Mode dynamique** : la cible est recalculee a chaque execution a partir du
  fichier source. Aucune copie figee.
- Strategie SQL : `MERGE` (upsert) sur `numero_document`.
  - `INSERT` si nouveau `numero_document` ;
  - `UPDATE` si `numero_document` existant et `raison_avoir` modifie ;
  - Pas de `DELETE` automatique (on conserve l'historique).
- Pour les `numero_document` absents du fichier a un run donne : on conserve la
  derniere valeur connue (pas d'ecrasement).

### 4.3 Normalisations a appliquer

- `.strip()` sur la valeur (suppression des espaces en debut / fin).
- Normalisation des espaces multiples en simple : `ERREUR DE  PREPARATION`
  -- `ERREUR DE PREPARATION`.
- Valeur vide (`''` / `None`) -- SQL `NULL` (et non chaine vide).

### 4.4 Cible proposee (a confirmer)

- Dataset / schema cible : `ebp_compta` (alignement avec les autres replications
  compta deja en place, cf. ticket `replicate_compta` precedent).
- Table cible : `ebp_compta.eurodelices_avoir_raison` (a valider avec l'equipe).
- Colonnes cibles minimales :
  - `numero_document` (PK, `VARCHAR(32)`)
  - `raison_avoir` (`VARCHAR(64)`, nullable)
  - `source_file` (`VARCHAR(255)`) -- pour tracabilite
  - `synced_at` (`TIMESTAMP`) -- horodatage de la derniere sync

---

## 5. Criteres d'acceptation

- [ ] **Dynamique** : la suppression du fichier source et la recreation avec une
      nouvelle valeur pour `Raison de l'avoir` propage bien la nouvelle valeur en
      cible au prochain run.
- [ ] **Non-figee** : aucun `COPY VALUES` static dans le code de replication ;
      toutes les valeurs viennent d'une lecture courante du fichier source.
- [ ] **Upsert idempotent** : 2 runs consecutifs produisent le meme etat cible
      (memes `COUNT(*)`, memes valeurs, pas de doublons).
- [ ] **Normalisation** : `ERREUR DE  PREPARATION` (double espace) est stocke en cible
      comme `ERREUR DE PREPARATION` (espace simple).
- [ ] **Volumetrie** : `COUNT(*)` cible = nombre de `numero_document` distincts
      dans la source (337, a confirmer apres dedoublonnage eventuel).
- [ ] **Tracabilite** : chaque ligne cible a un `synced_at` recent (< 5 minutes).
- [ ] **Cle stable** : le merge se fait bien sur `numero_document`, pas sur la
      position de ligne dans le fichier.
- [ ] **Logs** : compteurs `inserted / updated / skipped` emis a chaque run.

---

## 6. Implementation proposee (esquisse)

```
avoirs raisons.xls  -->  read_xls()  -->  normalize()  -->  build_dataframe()
                                                                |
                                                                v
                                                  merge into Postgres
                                                  (cible : ebp_compta.
                                                   eurodelices_avoir_raison)
```

Deux scripts, comme pour les tickets de replication compta existants :

1. `replicate_avoir_raison.py` -- incremental, idempotent, `MERGE` sur
   `numero_document`.
2. `replicate_avoir_raison_init.py` -- init complete (TRUNCATE + LOAD), reserve au
   premier chargement ou a une remise a zero validee.

---

## 7. Questions ouvertes (a trancher avant implementation)

1. **Cible** : confirmer `ebp_compta.eurodelices_avoir_raison` ou indiquer le
   schema / dataset exact.
2. **Frequence** : cron quotidien / a chaque export / declenche manuel ?
3. **Source perenne** : le `.xls` est-il remplace regulierement par un export
   ERP, ou faut-il se brancher directement sur la base source ?
4. **Lignes vides** : les 80 lignes sans `Raison de l'avoir` doivent-elles etre
   copiees avec `NULL`, ou filtrees a la source ?
5. **Typo** : la valeur `ERREUR DE  PREPARATION` reflete-t-elle l'orthographe
   metier, ou est-ce un defaut de qualite a corriger cote ERP en amont ?
6. **Perimetre temporel** : faut-il garder l'historique des changements de
   raison (versionning), ou juste la derniere valeur ?

---

## 8. References

- Fichier source : `C:\Users\KOURO\Desktop\metabase\avoirs raisons.xls`
- Tickets precedents lies : replication compta (cf. `replicate_compta*.py`,
  ticket [15.3]) -- voir `.gh/issue90.txt` pour le format de validation utilise.
- Conventions de replication du projet : `ebp_compta` + prefixe `eurodelices_`.

