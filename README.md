# Atelier Intégration des Données - OpenFoodFacts ETL

**M1 EISI / M1 CDPIA / M1 CYBER**
**Module:** TRDE703 Atelier Intégration des Données

## 📋 Description du Projet

Projet ETL Big Data qui construit un datamart "OpenFoodFacts Nutrition & Qualité" en utilisant **Apache Spark** (PySpark) pour l'extraction, la transformation et le chargement de données massives vers un datawarehouse **MySQL**.

Le projet implémente une architecture médaillon (Bronze → Silver → Gold) avec gestion de la qualité des données, modélisation en étoile (star schema), et SCD Type 2 pour l'historisation des produits.

## 🏗️ Architecture

```
┌─────────────────┐
│ OpenFoodFacts   │  Source: JSONL/CSV (données massives)
│   Data Export   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  BRONZE LAYER   │  Ingestion brute avec schéma explicite
│   (Parquet)     │  Job: etl/jobs/ingest.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SILVER LAYER   │  Nettoyage, normalisation, qualité
│   (Parquet)     │  Job: etl/jobs/conform.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   GOLD LAYER    │  Modèle en étoile (Star Schema)
│  MySQL Datamart │  Jobs: load_dimensions.py, load_product_scd.py, load_fact.py
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Quality Report │  Métriques & anomalies
│   & Analytics   │  Job: quality_report.py + SQL queries
└─────────────────┘
```

### Modèle de Données (Star Schema)

**Dimensions:**
- `dim_brand` - Marques
- `dim_category` - Catégories de produits
- `dim_country` - Pays
- `dim_time` - Dimension temporelle (YYYYMMDD)
- `dim_product` - Produits (SCD Type 2)

**Faits:**
- `fact_nutrition_snapshot` - Mesures nutritionnelles (100g) avec scores qualité

Voir `docs/architecture.md` pour les détails complets.

## 📂 Structure du Projet

```
OpenFoodFact/
├── etl/                        # Code source ETL (PySpark)
│   ├── main.py                # Orchestrateur principal
│   ├── settings.py            # Configuration
│   ├── utils.py               # Utilitaires Spark
│   ├── schema_bronze.py       # Schémas explicites
│   └── jobs/                  # Jobs ETL (6 fichiers)
├── sql/                        # Scripts SQL
│   ├── schema.sql             # DDL tables
│   ├── init_dimensions.sql    # Init dimensions
│   └── analysis_queries.sql   # Requêtes analytiques
├── tests/                      # Tests unitaires
│   ├── test_etl.py
│   └── sample_data.jsonl
├── docs/                       # Documentation
│   ├── architecture.md
│   ├── CAHIER_DE_QUALITE.md
│   └── DATA_DICTIONARY.md
├── conf/                       # Configuration
│   └── config.yaml
├── scripts/                    # Scripts utilitaires
│   └── docker_init.sh
├── data/                       # Data Lake (généré)
├── docker-compose.yml         # Services Docker
├── Dockerfile                 # Image ETL
├── Makefile                   # Commandes simplifiées
└── README.md

Voir PROJECT_STRUCTURE.md pour plus de détails.
```

## 🚀 Installation & Configuration

### Option 1: Docker (Recommandé) 🐳

**La solution la plus simple et reproductible!**

#### Prérequis
- Docker >= 20.10
- Docker Compose >= 1.29
- Make (optionnel mais recommandé)

#### Installation Rapide (3 commandes)

```bash
# 1. Cloner le dépôt
git clone <repo_url>
cd OpenFoodFact

# 2. Construire et démarrer les services
make build && make up

# 3. Exécuter l'ETL avec données de test
make etl-test
```

**C'est tout!** MySQL, PySpark, et toutes les dépendances sont configurés automatiquement.

#### Commandes Utiles

```bash
# Voir toutes les commandes disponibles
make help

# Gestion des services
make up              # Démarrer les services
make down            # Arrêter les services
make logs            # Voir les logs
make ps              # État des services

# Exécution ETL
make etl-test        # Données de test
make etl-full        # Dataset complet (après make download)
make etl-skip        # Réutiliser Bronze existant

# Développement
make shell           # Shell dans conteneur ETL
make mysql-shell     # Console MySQL
make test            # Tests unitaires
```

**📖 Voir QUICKSTART.md pour démarrer rapidement**

---

### Option 2: Installation Manuelle

#### Prérequis

- **Python 3.10+** avec pip
- **Java 11 ou 17** (pour PySpark)
- **MySQL 8.0+**
- **Git**

#### Installation

1. **Cloner le dépôt**
   ```bash
   git clone <repo_url>
   cd OpenFoodFact
   ```

2. **Installer les dépendances Python**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer Java (vérifier)**
   ```bash
   java -version
   # Doit afficher Java 11 ou 17
   ```

4. **Configurer MySQL**
   ```bash
   # Créer la base de données
   mysql -u root -p < sql/schema.sql
   mysql -u root -p off_datamart < sql/init_dimensions.sql
   ```

5. **Télécharger les données OpenFoodFacts** (optionnel)
   ```bash
   python download_dump.py
   # Télécharge ~5GB de données compressées
   ```

#### Configuration

Variables d'environnement:

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=off_datamart
export DB_USER=root
export DB_PASSWORD=password
```

## 💻 Utilisation

### Option 1: Pipeline Complet (Recommandé)

```bash
# Avec données de test
python -m etl.main tests/sample_data.jsonl

# Avec données complètes OpenFoodFacts
python -m etl.main data/openfoodfacts-products.jsonl

# Skip ingestion (utiliser données Bronze existantes)
python -m etl.main --skip-ingest
```

### Option 2: Jobs Individuels

```bash
# 1. Bronze: Ingestion
python -m etl.jobs.ingest tests/sample_data.jsonl

# 2. Silver: Conformation
python -m etl.jobs.conform

# 3. Gold: Charger dimensions
python -m etl.jobs.load_dimensions

# 4. Gold: Charger produits (SCD2)
python -m etl.jobs.load_product_scd

# 5. Gold: Charger faits
python -m etl.jobs.load_fact

# 6. Générer rapport qualité
python -m etl.jobs.quality_report
```

### Option 3: Jupyter Notebook (Exploration Interactive)

```bash
jupyter notebook
# Ouvrir: projet/OpenFoodFacts_ETL_Workshop.ipynb
```

## 📊 Requêtes Analytiques

Après chargement du datamart, exécuter les requêtes dans `sql/analysis_queries.sql`:

```sql
-- Top 10 marques par proportion Nutri-Score A/B
SELECT ...

-- Distribution Nutri-Score par catégorie
SELECT ...

-- Heatmap pays × catégorie : moyenne sucres
SELECT ...

-- Taux de complétude par marque
SELECT ...

-- Anomalies détectées
SELECT ...

-- Évolution hebdomadaire complétude
SELECT ...
```

Voir le fichier complet pour toutes les requêtes disponibles.

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/test_etl.py -v

# Tests spécifiques
pytest tests/test_etl.py::TestUtils -v
pytest tests/test_etl.py::TestQualityRules -v

# Avec coverage
pytest tests/test_etl.py --cov=etl --cov-report=html
```

## 📈 Qualité des Données

Le pipeline implémente plusieurs règles de qualité:

### Règles de Nettoyage (Silver)
- ✅ Normalisation des tags (suppression préfixes langue)
- ✅ Conversion unités (sel = sodium × 2.5)
- ✅ Dédoublonnage par code-barres
- ✅ Résolution noms produits (priorité: fr > en > fallback)

### Règles de Validation
- ✅ **Bornes:** Nutriments dans intervalles raisonnables (ex: 0 ≤ sugars_100g ≤ 100)
- ✅ **Complétude:** Score pondéré de présence des champs clés
- ✅ **Cohérence:** Détection incohérences (énergie négative, etc.)

### Métriques Suivies
- Taux de complétude par champ
- Distribution des scores qualité
- Nombre d'anomalies par type
- Évolution temporelle de la qualité

Voir `docs/CAHIER_DE_QUALITE.md` pour les détails complets.

## 🔄 SCD Type 2 (Slowly Changing Dimensions)

Les produits sont historisés avec SCD Type 2:

```sql
SELECT * FROM dim_product WHERE code = '3017620422003';
```

| product_sk | code | product_name | is_current | effective_from | effective_to |
|------------|------|-------------|-----------|---------------|--------------|
| 1 | 3017620422003 | Nutella | 0 | 2023-01-01 | 2023-06-15 |
| 234 | 3017620422003 | Nutella Nouvelle Recette | 1 | 2023-06-15 | NULL |

## 📝 Livrables du Projet

- ✅ **Repo Git structuré** avec code source complet
- ✅ **Pipeline Spark reproductible** (Bronze → Silver → Gold)
- ✅ **Datamart MySQL** avec modèle en étoile
- ✅ **Scripts DDL/DML** pour création et analyse
- ✅ **Cahier de qualité** avec règles et métriques
- ✅ **Requêtes analytiques** répondant aux KPI métiers
- ✅ **Note d'architecture** avec choix techniques
- ✅ **Tests unitaires** pour validation
- ✅ **Documentation complète** (README, guides)

## 🎯 KPI & Questions Métiers

Le datamart répond aux questions suivantes:

1. ✅ Répartition Nutri-Score par catégorie / marque / pays
2. ✅ Évolution complétude des nutriments dans le temps
3. ✅ Taux d'anomalies (valeurs hors bornes)
4. ✅ Classement marques par qualité nutritionnelle moyenne
5. ✅ Top catégories avec le plus de transformation (NOVA)
6. ✅ Heatmap nutritionnelle pays × catégorie
7. ✅ Produits nécessitant amélioration des données

## 🛠️ Technologies Utilisées

- **PySpark 3.5** - Traitement distribué Big Data
- **MySQL 8.0** - Data Warehouse relationnel
- **Python 3.10** - Langage principal
- **Parquet** - Format stockage Data Lake
- **Docker** - Conteneurisation services
- **Jupyter** - Exploration interactive
- **pytest** - Framework de tests

## 📖 Documentation Complète

- 📄 [Architecture détaillée](docs/architecture.md)
- 📄 [Cahier de qualité](docs/CAHIER_DE_QUALITE.md)
- 📄 [Dictionnaire de données](docs/DATA_DICTIONARY.md)
- 📄 [Requêtes analytiques](sql/analysis_queries.sql)

## 🐛 Dépannage

### Erreur Java not found
```bash
# Installer Java 17
sudo apt install openjdk-17-jre-headless  # Linux
brew install openjdk@17                     # macOS

# Configurer JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### Erreur MySQL connection refused
```bash
# Vérifier que MySQL est démarré
docker-compose ps
docker-compose up -d mysql

# Tester connexion
mysql -h localhost -u root -p -e "SELECT 1"
```

### Erreur mémoire Spark
```bash
# Augmenter mémoire driver
export SPARK_DRIVER_MEMORY=4g
python -m etl.main <input_file>
```

## 👥 Auteurs

**Équipe M1 EISI/CDPIA/CYBER**
Année universitaire 2024-2025

## 📜 Licence

Projet académique - M1 Data Science & AI

## 🔗 Ressources Externes

- [OpenFoodFacts](https://world.openfoodfacts.org) - Source des données
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [MySQL 8.0 Reference](https://dev.mysql.com/doc/refman/8.0/en/)

---

**Note:** Ce projet a été réalisé dans le cadre du module TRDE703 "Atelier Intégration des Données" avec utilisation autorisée de ChatGPT/Claude comme assistant.
