# 📁 Structure du Projet

Structure organisée et minimaliste du projet ETL OpenFoodFacts.

## 🏗️ Arborescence

```
OpenFoodFact/
├── 📄 README.md                    # Documentation principale
├── 📄 QUICKSTART.md                # Guide démarrage rapide
│
├── 🐳 Docker & Configuration
│   ├── Dockerfile                  # Image ETL (Python + Spark + Java)
│   ├── docker-compose.yml          # Services (MySQL + ETL)
│   ├── .dockerignore               # Exclusions build Docker
│   ├── entrypoint.sh               # Script init conteneurs
│   ├── .env.example                # Template configuration
│   └── Makefile                    # Commandes simplifiées
│
├── 📂 etl/                         # Code source ETL
│   ├── __init__.py
│   ├── main.py                     # Orchestrateur pipeline
│   ├── settings.py                 # Configuration
│   ├── utils.py                    # Utilitaires Spark
│   ├── schema_bronze.py            # Schémas données
│   └── jobs/                       # Jobs ETL
│       ├── __init__.py
│       ├── ingest.py               # Bronze: Ingestion
│       ├── conform.py              # Silver: Nettoyage
│       ├── load_dimensions.py      # Gold: Dimensions
│       ├── load_product_scd.py     # Gold: Produits SCD2
│       ├── load_fact.py            # Gold: Faits
│       └── quality_report.py       # Rapport qualité
│
├── 📂 sql/                         # Scripts SQL
│   ├── schema.sql                  # DDL: Création tables
│   ├── init_dimensions.sql         # Init & vues
│   └── analysis_queries.sql        # Requêtes analytiques
│
├── 📂 tests/                       # Tests unitaires
│   ├── __init__.py
│   ├── test_etl.py                 # Tests PySpark
│   └── sample_data.jsonl           # Données test
│
├── 📂 docs/                        # Documentation
│   ├── architecture.md             # Architecture ETL
│   ├── CAHIER_DE_QUALITE.md        # Règles qualité
│   └── DATA_DICTIONARY.md          # Dictionnaire données
│
├── 📂 conf/                        # Configuration
│   └── config.yaml                 # Paramètres ETL
│
├── 📂 scripts/                     # Scripts utilitaires
│   └── docker_init.sh              # Setup automatique
│
├── 📂 data/                        # Data Lake (généré)
│   ├── bronze/                     # Données brutes
│   ├── silver/                     # Données nettoyées
│   ├── gold/                       # Données modélisées
│   └── quality_reports/            # Rapports qualité
│
├── 📂 projet/                      # Notebooks Jupyter
│   └── OpenFoodFacts_ETL_Workshop.ipynb
│
├── 📂 logs/                        # Logs (généré)
├── 📂 backups/                     # Backups MySQL (généré)
│
├── .gitignore                      # Exclusions Git
└── requirements.txt                # Dépendances Python
```

## 📊 Statistiques

- **Fichiers Python**: 13
- **Scripts SQL**: 3
- **Documentation**: 5 fichiers
- **Configuration**: 6 fichiers
- **Tests**: 2 fichiers

## 🎯 Fichiers Essentiels

### Configuration & Déploiement (7)
```
Dockerfile                    # Image Docker ETL
docker-compose.yml            # Orchestration services
Makefile                      # Automatisation commandes
entrypoint.sh                 # Init conteneurs
.env.example                  # Template config
.dockerignore                 # Optimisation build
.gitignore                    # Exclusions Git
```

### Code ETL (8)
```
etl/main.py                   # Pipeline principal
etl/settings.py               # Configuration
etl/utils.py                  # Helpers Spark
etl/schema_bronze.py          # Schémas
etl/jobs/ingest.py            # Job Bronze
etl/jobs/conform.py           # Job Silver
etl/jobs/load_*.py            # Jobs Gold (3 fichiers)
etl/jobs/quality_report.py    # Qualité
```

### SQL & Base de Données (3)
```
sql/schema.sql                # DDL tables
sql/init_dimensions.sql       # Init dimensions
sql/analysis_queries.sql      # Requêtes analytiques
```

### Tests (2)
```
tests/test_etl.py             # Tests unitaires
tests/sample_data.jsonl       # Données test
```

### Documentation (5)
```
README.md                     # Doc principale
QUICKSTART.md                 # Guide rapide
docs/architecture.md          # Architecture
docs/CAHIER_DE_QUALITE.md     # Qualité
docs/DATA_DICTIONARY.md       # Dictionnaire
```

## 🚫 Fichiers Exclus (.gitignore)

### Données (générées localement)
```
data/bronze/
data/silver/
data/gold/
data/quality_reports/
data/*.jsonl
data/*.gz
```

### Environnement
```
.env                          # Secrets locaux
__pycache__/                  # Cache Python
.ipynb_checkpoints/           # Checkpoints Jupyter
```

### Système
```
logs/                         # Logs d'exécution
backups/                      # Backups MySQL
```

## 🔄 Flux de Données

```
1. Source (JSONL)
   ↓
2. data/bronze/     (Parquet brut)
   ↓
3. data/silver/     (Parquet nettoyé)
   ↓
4. MySQL Gold       (Tables relationnelles)
   ↓
5. data/quality_reports/ (JSON)
```

## 🎓 Organisation par Couche

### Bronze Layer
- **Fichier**: `etl/jobs/ingest.py`
- **Input**: JSONL brut
- **Output**: `data/bronze/` (Parquet)
- **Fonction**: Ingestion avec schéma explicite

### Silver Layer
- **Fichier**: `etl/jobs/conform.py`
- **Input**: `data/bronze/`
- **Output**: `data/silver/` (Parquet)
- **Fonction**: Nettoyage, validation, normalisation

### Gold Layer
- **Fichiers**: `load_dimensions.py`, `load_product_scd.py`, `load_fact.py`
- **Input**: `data/silver/`
- **Output**: MySQL (tables)
- **Fonction**: Modélisation en étoile + SCD2

### Quality Layer
- **Fichier**: `etl/jobs/quality_report.py`
- **Input**: `data/silver/`
- **Output**: `data/quality_reports/` (JSON)
- **Fonction**: Analyse qualité, métriques, anomalies

## 🛠️ Utilisation

### Setup Initial
```bash
# Copier la config
cp .env.example .env

# Initialiser Docker
bash scripts/docker_init.sh

# Démarrer services
make up
```

### Exécution ETL
```bash
# Pipeline complet
make etl-test

# Jobs individuels
python -m etl.jobs.ingest tests/sample_data.jsonl
python -m etl.jobs.conform
python -m etl.jobs.load_dimensions
```

### Développement
```bash
# Shell ETL
make shell

# Console MySQL
make mysql-shell

# Tests
make test
```

## 📝 Notes

- **Data Lake**: Dossier `data/` exclu de Git (trop volumineux)
- **Logs**: Dossier `logs/` exclu de Git
- **Secrets**: Fichier `.env` exclu de Git
- **Jupyter**: Notebook disponible, exécutable via votre IDE
- **Backups**: Dossier `backups/` pour sauvegardes MySQL

## 🎯 Pour le Rendu

**Fichiers à inclure dans le rapport:**
1. README.md - Vue d'ensemble
2. QUICKSTART.md - Instructions reproduction
3. docs/architecture.md - Architecture technique
4. docs/CAHIER_DE_QUALITE.md - Qualité des données
5. Capture d'écran exécution ETL
6. Export résultats SQL

**Fichiers à mentionner:**
- docker-compose.yml - Infrastructure
- Makefile - Automatisation
- Tests validés - tests/test_etl.py

---

**Structure organisée, minimaliste et professionnelle** ✨
