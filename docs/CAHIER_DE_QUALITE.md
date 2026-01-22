# Cahier de Qualité - OpenFoodFacts Datamart

## 1. Stratégie de Qualité des Données

La qualité des données est assurée à chaque étape du pipeline ETL (Bronze -> Silver -> Gold).
Nous appliquons une stratégie de **"Filter & Flag"** :
*   Nous ne rejetons pas silencieusement les lignes sauf si elles sont inexploitables (pas de code-barres).
*   Nous marquons les problèmes de qualité (flag `quality_issues_json` et score `completeness_score`).

## 2. Règles de Nettoyage (Silver Layer)

### 2.1 Normalisation
*   **Strings** : Trimming des espaces.
*   **Tags** : Suppression des préfixes `en:`, `fr:` pour les `countries_tags` et `categories_tags`.
*   **Unités** : Conversion de sélénium/sodium si nécessaire (Ex: `salt = sodium * 2.5` si salt est null).

### 2.2 Dédoublonnage
*   Critère : Unicité sur le champ `code` (EAN-13).
*   Règle : En cas de doublon, on conserve la ligne ayant le `last_modified_t` le plus récent.

## 3. Métriques Suivies

Le job `etl/jobs/quality_report.py` génère les métriques suivantes à chaque exécution :

| Métrique | Description | Seuil d'alerte |
| :--- | :--- | :--- |
| **Nutri-Score Completeness** | % de produits ayant un Nutri-Score valide. | < 50% |
| **Aberrant Sugars** | Nombre de produits avec `sugars_100g > 100`. | > 0 |
| **Negative Energy** | Nombre de produits avec `energy_kcal < 0`. | > 0 |

## 4. Anomalies et Gestion

### Détection
Les anomalies sont détectées lors du chargement Gold.
*   **Bornes** : `sugars_100g` > 100g.
*   **Cohérence** : `energy_kcal` trop élevé (> 900 kcal/100g est suspect, sauf huiles).

### Action
*   Ces anomalies sont stockées dans la colonne `quality_issues_json` de la table de faits.
*   Elles peuvent être auditées via la requête SQL n°5 fournie dans `sql/analysis_queries.sql`.
