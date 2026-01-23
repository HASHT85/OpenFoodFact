# Dictionnaire de Données - OpenFoodFacts Datamart

## Vue d'Ensemble

Ce document décrit tous les champs et tables du datamart OpenFoodFacts.

## Tables Dimensionnelles

### dim_brand (Marques)

Dimension des marques de produits.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| brand_sk | INT | ✓ | ✗ | Clé surrogate de la marque (auto-increment) |
| brand_name | VARCHAR(255) | | ✗ | Nom de la marque (unique) |

**Volume estimé:** 50,000 - 100,000 marques

**Exemples:** Ferrero, Coca Cola, Danone, Nestlé

---

### dim_category (Catégories)

Dimension des catégories de produits.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| category_sk | INT | ✓ | ✗ | Clé surrogate de la catégorie |
| category_code | VARCHAR(255) | | ✗ | Code de catégorie (unique, ex: "spreads") |
| category_name_fr | VARCHAR(255) | | ✓ | Libellé français de la catégorie |
| level | INT | | ✓ | Niveau hiérarchique (1=racine) |
| parent_category_sk | INT | | ✓ | FK vers catégorie parente (auto-référence) |

**Volume estimé:** 10,000 - 20,000 catégories

**Exemples:**
- code: "breakfasts", category_name_fr: "Petits déjeuners", level: 1
- code: "spreads", category_name_fr: "Pâtes à tartiner", level: 2

**Note:** Dans la version actuelle, la hiérarchie n'est pas complètement implémentée (level=1 pour tous).

---

### dim_country (Pays)

Dimension des pays de vente/fabrication.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| country_sk | INT | ✓ | ✗ | Clé surrogate du pays |
| country_code | VARCHAR(10) | | ✗ | Code pays (unique, ex: "france", "usa") |
| country_name_fr | VARCHAR(255) | | ✓ | Libellé français du pays |

**Volume estimé:** 200-300 pays/régions

**Exemples:**
- code: "france", name: "France"
- code: "usa", name: "États-Unis"
- code: "italy", name: "Italie"

---

### dim_time (Dimension Temporelle)

Dimension de dates pré-calculée.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| time_sk | INT | ✓ | ✗ | Clé surrogate au format YYYYMMDD |
| date | DATE | | ✓ | Date au format DATE |
| year | INT | | ✓ | Année (ex: 2024) |
| month | INT | | ✓ | Mois (1-12) |
| day | INT | | ✓ | Jour du mois (1-31) |
| week | INT | | ✓ | Numéro de semaine dans l'année |
| iso_week | INT | | ✓ | Numéro de semaine ISO 8601 |

**Volume:** 3653 enregistrements (2020-01-01 à 2030-12-31)

**Exemple:**
- time_sk: 20240315
- date: 2024-03-15
- year: 2024, month: 3, day: 15, iso_week: 11

**Usage:** Jointure sur `time_sk` depuis la table de faits pour analyse temporelle.

---

### dim_product (Produits - SCD Type 2)

Dimension des produits avec historisation SCD Type 2.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| product_sk | INT | ✓ | ✗ | Clé surrogate du produit (auto-increment) |
| code | VARCHAR(50) | | ✗ | Code-barres EAN-13 (clé naturelle) |
| product_name | TEXT | | ✓ | Nom du produit |
| brand_sk | INT | FK | ✓ | Clé surrogate de la marque |
| primary_category_sk | INT | FK | ✓ | Clé surrogate de la catégorie principale |
| countries_multi | JSON | | ✓ | Array JSON des pays (["france", "belgium"]) |
| is_current | BOOLEAN | | ✗ | Flag indiquant la version actuelle (1=oui, 0=historique) |
| effective_from | TIMESTAMP | | ✓ | Date de début de validité |
| effective_to | TIMESTAMP | | ✓ | Date de fin de validité (NULL si actuel) |
| row_hash | VARCHAR(32) | | ✓ | Hash MD5 pour détection de changements |

**Volume estimé:** 1-3 millions produits × 1.2 (avec historique)

**Clés étrangères:**
- brand_sk → dim_brand(brand_sk)
- primary_category_sk → dim_category(category_sk)

**Index:**
- idx_code_current (code, is_current) - Pour retrouver version actuelle
- idx_brand (brand_sk) - Pour agrégation par marque
- idx_category (primary_category_sk) - Pour agrégation par catégorie

**Exemple SCD2:**
```
| product_sk | code | product_name | brand_sk | is_current | effective_from | effective_to |
|------------|------|-------------|----------|-----------|----------------|--------------|
| 1 | 301762 | Nutella | 5 | 0 | 2023-01-01 | 2023-06-15 |
| 234 | 301762 | Nutella Bio | 5 | 1 | 2023-06-15 | NULL |
```

---

### dim_nutri (Scores Nutritionnels - Optionnel)

Dimension optionnelle pour les scores nutritionnels.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| nutri_sk | INT | ✓ | ✗ | Clé surrogate |
| nutriscore_grade | CHAR(1) | | ✓ | Grade Nutri-Score (a, b, c, d, e) |
| nutriscore_score_min | INT | | ✓ | Score minimum pour ce grade |
| nutriscore_score_max | INT | | ✓ | Score maximum pour ce grade |
| nova_group | INT | | ✓ | Groupe NOVA (1-4) |
| nova_description | VARCHAR(255) | | ✓ | Description du groupe NOVA |
| ecoscore_grade | CHAR(1) | | ✓ | Grade Eco-Score (a-e) |

**Volume:** ~125 combinaisons (5 nutriscore × 5 ecoscore × 4 nova)

**Note:** Non utilisé dans la version actuelle mais prêt pour extension.

---

## Table de Faits

### fact_nutrition_snapshot (Instantanés Nutritionnels)

Table de faits contenant les mesures nutritionnelles par produit et date.

| Colonne | Type | PK | Nullable | Mesure/Attribut | Description |
|---------|------|----|---------| --------------- | ------------|
| fact_id | BIGINT | ✓ | ✗ | - | Clé primaire (auto-increment) |
| product_sk | INT | FK | ✗ | - | Clé surrogate du produit |
| time_sk | INT | FK | ✗ | - | Clé surrogate de la date (YYYYMMDD) |
| **Mesures Nutritionnelles (pour 100g)** |
| energy_kcal_100g | DECIMAL(10,2) | | ✓ | Mesure | Énergie en kcal |
| fat_100g | DECIMAL(10,2) | | ✓ | Mesure | Matières grasses totales (g) |
| saturated_fat_100g | DECIMAL(10,2) | | ✓ | Mesure | Acides gras saturés (g) |
| sugars_100g | DECIMAL(10,2) | | ✓ | Mesure | Sucres (g) |
| salt_100g | DECIMAL(10,2) | | ✓ | Mesure | Sel (g) |
| proteins_100g | DECIMAL(10,2) | | ✓ | Mesure | Protéines (g) |
| fiber_100g | DECIMAL(10,2) | | ✓ | Mesure | Fibres alimentaires (g) |
| sodium_100g | DECIMAL(10,2) | | ✓ | Mesure | Sodium (g) [sel = sodium × 2.5] |
| **Scores & Grades** |
| nutriscore_grade | CHAR(1) | | ✓ | Attribut | Grade Nutri-Score (a-e) |
| nova_group | INT | | ✓ | Attribut | Groupe NOVA (1=minimal, 4=ultra-transformé) |
| ecoscore_grade | CHAR(1) | | ✓ | Attribut | Grade Eco-Score (a-e) |
| **Métriques Qualité** |
| completeness_score | DECIMAL(3,2) | | ✓ | Mesure | Score de complétude (0.00-1.00) |
| quality_issues_json | JSON | | ✓ | Attribut | JSON des anomalies détectées |

**Clés étrangères:**
- product_sk → dim_product(product_sk)
- time_sk → dim_time(time_sk) [optionnel, non forcé]

**Index:**
- idx_product_time (product_sk, time_sk) - Requêtes par produit/date
- idx_time (time_sk) - Agrégation temporelle
- idx_nutriscore (nutriscore_grade) - Filtrage par Nutri-Score
- idx_completeness (completeness_score) - Filtrage qualité

**Volume estimé:** 1-3 millions enregistrements (snapshot par produit par run ETL)

**Exemples de valeurs:**

```json
{
  "fact_id": 12345,
  "product_sk": 234,
  "time_sk": 20240315,
  "energy_kcal_100g": 539.00,
  "sugars_100g": 56.30,
  "fat_100g": 30.90,
  "salt_100g": 0.11,
  "nutriscore_grade": "e",
  "nova_group": 4,
  "completeness_score": 0.85,
  "quality_issues_json": "{}"
}
```

**quality_issues_json format:**
```json
{
  "energy_kcal_100g": false,
  "sugars_100g": false,
  "fat_100g": false,
  "salt_100g": false
}
```

---

## Tables de Pont (Bridge Tables - Optionnel)

### bridge_product_category

Table de pont pour relation N-N entre produits et catégories.

| Colonne | Type | PK | Nullable | Description |
|---------|------|----|---------| ------------|
| product_sk | INT | ✓ | ✗ | Clé du produit |
| category_sk | INT | ✓ | ✗ | Clé de la catégorie |

**Note:** Non utilisé dans la version actuelle mais disponible pour extension.

---

## Vues Utilitaires

### v_active_products

Vue des produits actifs avec détails.

**Colonnes:** product_sk, code, product_name, brand_name, primary_category, countries_multi, effective_from

**Usage:** Accès rapide aux produits en cours de validité.

---

### v_latest_nutrition_facts

Vue des dernières mesures nutritionnelles par produit.

**Colonnes:** Toutes colonnes de fact_nutrition_snapshot + détails dimensions

**Usage:** Analyse des valeurs nutritionnelles les plus récentes.

---

### v_brand_summary

Vue agrégée des statistiques par marque.

**Colonnes:** brand_name, total_products, avg_completeness, avg_sugars, distribution Nutri-Score

**Usage:** Dashboard et reporting marques.

---

### v_products_with_quality_issues

Vue des produits avec anomalies qualité.

**Colonnes:** code, product_name, brand_name, completeness_score, quality_issues_json, primary_issue

**Usage:** Audit qualité et remédiation.

---

## Règles de Gestion

### Bornes Acceptables (Nutriments pour 100g)

| Nutriment | Min | Max | Unité | Justification |
|-----------|-----|-----|-------|---------------|
| energy_kcal_100g | 0 | 900 | kcal | Max = huiles pures (~900 kcal) |
| sugars_100g | 0 | 100 | g | Ne peut dépasser 100g/100g |
| fat_100g | 0 | 100 | g | Ne peut dépasser 100g/100g |
| saturated_fat_100g | 0 | 100 | g | Sous-ensemble de fat_100g |
| salt_100g | 0 | 25 | g | Sel très élevé au-delà |
| sodium_100g | 0 | 10 | g | salt = sodium × 2.5 |
| proteins_100g | 0 | 100 | g | Max = poudres protéinées |
| fiber_100g | 0 | 100 | g | Max = suppléments fibres |

### Nutri-Score (OpenFoodFacts)

| Grade | Score | Interprétation |
|-------|-------|----------------|
| A | -15 à -1 | Meilleure qualité nutritionnelle |
| B | 0 à 2 | Bonne qualité |
| C | 3 à 10 | Qualité moyenne |
| D | 11 à 18 | Faible qualité |
| E | 19+ | Très faible qualité |

### NOVA Groups (Niveau de Transformation)

| Groupe | Description | Exemples |
|--------|-------------|----------|
| 1 | Aliments non transformés ou minimalement transformés | Fruits, légumes, lait |
| 2 | Ingrédients culinaires transformés | Huile, beurre, sucre, sel |
| 3 | Aliments transformés | Conserves, fromages, pain |
| 4 | Produits ultra-transformés | Sodas, snacks, plats préparés |

### Score de Complétude

**Formule:**
```
completeness_score = Σ (poids_i × présence_i)
```

**Poids des champs:**
- product_name: 20%
- brands: 15%
- categories: 15%
- nutriscore_grade: 10%
- energy_kcal_100g: 10%
- sugars_100g: 7.5%
- fat_100g: 7.5%
- saturated_fat_100g: 5%
- salt_100g: 5%
- proteins_100g: 7.5%
- fiber_100g: 5%

**Interprétation:**
- 0.80-1.00: Haute qualité
- 0.50-0.79: Qualité moyenne
- 0.00-0.49: Faible qualité

---

## Cardinalités

### Relations

```
dim_brand (1) ←──── (N) dim_product
dim_category (1) ←──── (N) dim_product
dim_product (1) ←──── (N) fact_nutrition_snapshot
dim_time (1) ←──── (N) fact_nutrition_snapshot
```

### Volumétrie Estimée

| Table | Enregistrements | Croissance |
|-------|----------------|------------|
| dim_brand | 100K | +10K/an |
| dim_category | 20K | +2K/an |
| dim_country | 300 | Stable |
| dim_time | 3653 | Stable (pré-chargé) |
| dim_product | 3M | +500K/an |
| fact_nutrition_snapshot | 3M | +500K/run |

---

## Conventions de Nommage

### Tables
- Dimensions: `dim_<nom>`
- Faits: `fact_<nom>`
- Ponts: `bridge_<nom>`
- Vues: `v_<nom>`
- Agrégats: `agg_<nom>`

### Colonnes
- Clés surrogate: `<table>_sk`
- Clés naturelles: nom explicite (ex: `code`, `brand_name`)
- Mesures: `<nom>_<unité>` (ex: `sugars_100g`)
- Flags: `is_<état>`, `has_<attribut>`
- Timestamps: `<action>_<from|to>` (ex: `effective_from`)

---

## Sources de Données

**Source principale:** OpenFoodFacts (https://world.openfoodfacts.org)
- Export complet: https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz
- Format: JSONL (JSON Lines)
- Mise à jour: Quotidienne
- Licence: Open Database License (ODbL)

**API (optionnel):**
- Base URL: https://world.openfoodfacts.org/api/v2
- Usage: Enrichissement ponctuel

---

## Glossaire

- **SCD Type 2:** Slowly Changing Dimension Type 2 - Méthode d'historisation conservant toutes les versions
- **Surrogate Key:** Clé artificielle générée (auto-increment) indépendante des données métier
- **Natural Key:** Clé métier existante (ex: code-barres)
- **Fact Table:** Table centrale d'un modèle en étoile contenant les mesures
- **Dimension Table:** Table de référence contenant les attributs descriptifs
- **Grain:** Niveau de détail d'une table de faits (ici: produit × date)

---

**Version:** 1.0.0
**Dernière mise à jour:** 2024-01-23
