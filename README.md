# Atelier Intégration des Données - OpenFoodFacts

Projet ETL Big Data pour l'intégration des données OpenFoodFacts dans un Datamart MySQL.

## Architecture

*   **ETL** : Apache Spark (PySpark)
*   **Storage** : Parquet (Bronze/Silver), MySQL (Gold)
*   **Modèle** : Schéma en étoile (Dimensions + Faits)

## Structure du Projet

*   `etl/` : Code source Spark
    *   `jobs/` : Scripts de jobs (ingest, conform, load)
    *   `main.py` : Orchestrateur
*   `sql/` : Scripts SQL (DDL, DML, Analyses)
*   `docs/` : Documentation (Architecture, Qualité)
*   `conf/` : Fichiers de configuration
*   `data/` : Dossier de sortie locale (Bronze/Silver)

## Installation

1.  Installer les dépendances : `pip install -r requirements.txt`
2.  Avoir Java installé (JAVA_HOME configuré).
3.  Avoir une instance MySQL locale.

## Usage

### Option 1 : Jupyter Notebook (Recommandé)
1.  Lancer Jupyter : `jupyter notebook`
2.  Aller dans le dossier `projet/`.
3.  Ouvrir `OpenFoodFacts_ETL_Workshop.ipynb`.

### Option 2 : Scripts Python
1.  Initialiser la BDD :
    ```bash
    mysql -u [user] -p < sql/schema.sql
    ```
2.  Lancer le pipeline :
    ```bash
    python etl/main.py /chemin/vers/openfoodfacts-products.jsonl
    ```

## Auteurs
M1 EISI / CDPIA / CYBER
