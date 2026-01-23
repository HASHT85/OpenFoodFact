# 🐳 Docker - OpenFoodFacts ETL

Configuration Docker simplifiée pour le projet ETL.

## 📦 Fichiers Docker

### Configuration
- `Dockerfile` - Image Python 3.10 + PySpark + Java 17 + MySQL
- `docker-compose.yml` - 3 services (MySQL, ETL, Jupyter)
- `.dockerignore` - Optimisation du build
- `entrypoint.sh` - Script d'initialisation
- `.env.example` - Template de configuration

### Automatisation
- `Makefile` - 30+ commandes simplifiées
- `scripts/docker_init.sh` - Setup automatique

## 🚀 Utilisation

### Installation (3 étapes)

```bash
# 1. Setup
bash scripts/docker_init.sh

# 2. Démarrer
make up

# 3. Exécuter ETL
make etl-test
```

### Commandes Principales

```bash
make help            # Liste toutes les commandes

# Services
make up              # Démarrer
make down            # Arrêter
make logs            # Logs
make ps              # Statut

# ETL
make etl-test        # Test avec données échantillon
make etl-full        # Pipeline complet
make etl-skip        # Réutiliser Bronze existant

# Développement
make shell           # Shell ETL
make mysql-shell     # Console MySQL
make jupyter         # Jupyter Lab
make test            # Tests
```

## 📋 Services

### MySQL
- Port: 3306
- Database: off_datamart
- User: root
- Password: password (changeable dans .env)

### ETL (PySpark)
- Python 3.10
- PySpark 3.5
- Java 17
- Volumes montés pour hot-reload

### Jupyter (optionnel)
- Port: 8888
- Accès: http://localhost:8888
- Démarrer: `make jupyter`

## 🔧 Configuration

Créer `.env` depuis le template:

```bash
cp .env.example .env
```

Personnaliser:

```bash
# Base de données
DB_PORT=3306
DB_NAME=off_datamart
DB_ROOT_PASSWORD=password

# Spark
SPARK_DRIVER_MEMORY=2g
SPARK_EXECUTOR_MEMORY=2g

# Jupyter
JUPYTER_PORT=8888
```

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│       Docker Compose Stack          │
│                                     │
│  ┌────────┐  ┌────────┐  ┌───────┐│
│  │ MySQL  │  │  ETL   │  │Jupyter││
│  │ :3306  │◄─┤PySpark │  │ :8888 ││
│  └────────┘  └────────┘  └───────┘│
│         off_network                │
└─────────────────────────────────────┘
       │            │           │
  [mysql_data] [./data/]  [jupyter_data]
```

## 🧪 Workflow

### Développement

```bash
# 1. Démarrer
make up

# 2. Modifier le code localement
# Les fichiers etl/ sont montés en volume

# 3. Tester immédiatement
make test

# 4. Exécuter ETL
make etl-test
```

### Debug

```bash
# Shell interactif
make shell

# Logs en temps réel
make logs-etl

# Vérifier base de données
make mysql-shell
```

## 🆘 Dépannage

### Services ne démarrent pas

```bash
make build
make up
make logs
```

### Erreur MySQL

```bash
make down
docker volume rm off_mysql_data
make up
```

### Erreur mémoire Spark

```bash
echo "SPARK_DRIVER_MEMORY=4g" >> .env
make restart
```

### Port occupé

```bash
# Changer le port dans .env
echo "DB_PORT=3307" >> .env
make down && make up
```

## 📊 Avantages

✅ **Installation simplifiée** - 3 commandes vs 20+
✅ **Reproductible** - Fonctionne sur Win/Linux/Mac
✅ **Isolé** - Pas de conflit avec système
✅ **Hot-reload** - Modifications instantanées
✅ **Complet** - MySQL + Spark + Jupyter

## 📚 Documentation

- **QUICKSTART.md** - Guide de démarrage rapide
- **README.md** - Vue d'ensemble du projet
- **docs/architecture.md** - Architecture ETL
- **docs/CAHIER_DE_QUALITE.md** - Qualité des données

## 🎯 Pour le Rendu

```bash
# Pipeline complet
make build && make up && make etl-test

# Générer livrables
make logs-etl > logs.txt
cat data/quality_reports/*.json > qualite.json

# Vérifier résultats
make mysql-shell
```

---

**Installation en 3 commandes. Exécution en 2 minutes.** 🚀
