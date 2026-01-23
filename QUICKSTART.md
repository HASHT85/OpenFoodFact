# 🚀 Quick Start - OpenFoodFacts ETL

Guide de démarrage rapide en 5 minutes avec Docker.

## ⚡ Installation (3 commandes)

```bash
# 1. Cloner le projet
git clone <repo_url>
cd OpenFoodFact

# 2. Initialiser Docker
bash scripts/docker_init.sh

# 3. Démarrer
make up && make etl-test
```

## 📋 Commandes Essentielles

```bash
# Voir toutes les commandes
make help

# Services
make up              # Démarrer MySQL + ETL
make down            # Arrêter
make logs            # Voir les logs
make ps              # Statut

# ETL
make etl-test        # Pipeline avec données de test
make etl-full        # Pipeline complet (après make download)
make download        # Télécharger dataset OpenFoodFacts (~5GB)

# Développement
make shell           # Shell dans conteneur ETL
make mysql-shell     # Console MySQL
make jupyter         # Jupyter Lab (http://localhost:8888)
make test            # Tests unitaires
```

## ✅ Vérification

```bash
# Voir les résultats dans MySQL
make mysql-shell
```

```sql
-- Dans MySQL
SHOW TABLES;
SELECT COUNT(*) FROM fact_nutrition_snapshot;
SELECT nutriscore_grade, COUNT(*) FROM fact_nutrition_snapshot
GROUP BY nutriscore_grade;
exit
```

## 🔧 Configuration

Modifier `.env` pour personnaliser:

```bash
# Mémoire Spark
SPARK_DRIVER_MEMORY=4g

# Ports
DB_PORT=3306
JUPYTER_PORT=8888
```

## 🆘 Dépannage Rapide

```bash
# Problème de démarrage
make build
make up

# Voir les erreurs
make logs

# Réinitialiser tout
make clean
make up
```

## 📚 Documentation

- **README.md** - Vue d'ensemble complète
- **docs/architecture.md** - Architecture détaillée
- **docs/CAHIER_DE_QUALITE.md** - Règles de qualité
- **docs/DATA_DICTIONARY.md** - Dictionnaire de données

## 🎯 Pour le Rendu Académique

```bash
# 1. Exécuter le pipeline
make etl-test

# 2. Générer les résultats
make logs-etl > logs_execution.txt
cat data/quality_reports/quality_report_*.json > rapport_qualite.json

# 3. Requêtes SQL
make mysql-shell < sql/analysis_queries.sql > resultats_sql.txt
```

---

**Prêt en 5 minutes!** 🚀
