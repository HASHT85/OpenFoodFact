# Note d'Architecture - Atelier Intégration des Données (OpenFoodFacts)

## 1. Choix Techniques

*   **Langage & ETL** : Python avec **PySpark**.
    *   *Justification* : Python est le standard de facto pour la data science. Spark permet le traitement distribué nécessaire pour les "données massives" d'OpenFoodFacts.
*   **Stockage (Datalake)** : Système de fichiers local (simulant HDFS/S3) pour les couches Bronze/Silver (Parquet/JSON).
*   **Data Warehouse** : **MySQL 8**.
    *   *Justification* : SGBD relationnel robuste, cible explicite du sujet.
*   **Orchestration** : Scripts Python séquentiels (pour simplifier le workshop, sinon Airflow en prod).

## 2. Architecture de Données (Medallion Architecture)

### Bronze (Raw)
*   **Source** : Exports JSONL OpenFoodFacts.
*   **Format** : Parquet (après ingestion brute) ou lecture directe JSON.
*   **Traitement** : Lecture, sélection des colonnes brutes, pas de modification de valeur.

### Silver (Clean & Conformed)
*   **Format** : Parquet.
*   **Traitements** :
    *   **Nettoyage** : Trimming, casts, gestion des NULLs / valeurs aberrantes.
    *   **Normalisation** : Conversion des unités (ex: kj -> kcal si nécessaire, mg -> g).
    *   **Dédoublonnage** : Conservation de la version la plus récente (`last_modified_t`) pour chaque `code`.
    *   **Taxonomies** : Mapping des tags (categories_tags, countries_tags) vers des libellés propres via les taxonomies OFF.

### Gold (Presentation)
*   **Cible** : MySQL (Star Schema).
*   **Modèle** :
    *   **Dimensions** : `dim_product`, `dim_brand`, `dim_category`, `dim_country`, `dim_time`.
    *   **Faits** : `fact_nutrition_snapshot`.
*   **SCD Type 2** : Sur `dim_product` pour suivre l'évolution des métadonnées (nom, marque, catégories) dans le temps.

## 3. Stratégie d'Alimentation (Upsert & SCD)

*   **Petites Dimensions (Brand, Category, Country)** :
    *   **Truncate-Insert** (si volumétrie faible) ou **Insert-Ignore** pour les nouvelles valeurs.
*   **Produits (`dim_product`)** :
    *   **SCD2** : Comparaison du hash des attributs suivis entre la version entrante et la version active en base.
    *   Si changement : Clôture (`is_current=0`, `effective_to=now`) et Insertion nouvelle ligne (`is_current=1`, `effective_from=now`).
*   **Faits (`fact_nutrition_snapshot`)** :
    *   Append-only typiquement, relié à la `product_sk` active au moment de l'import.
