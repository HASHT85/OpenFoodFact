# 🧪 Guide de Test - OpenFoodFacts ETL

Guide complet pour tester votre projet dockerisé.

## ✅ Checklist de Test

### Phase 1: Prérequis (2 min)

```bash
# 1. Vérifier Docker
docker --version
docker-compose --version

# 2. Vérifier que Docker tourne
docker ps

# 3. Se placer dans le projet
cd C:\Projet\OFF\OpenFoodFact
```

**Résultat attendu:**
- Docker version 20.10+
- Docker Compose version 1.29+
- Commande `docker ps` fonctionne

---

### Phase 2: Configuration (1 min)

```bash
# 1. Créer le fichier .env
cp .env.example .env

# 2. Vérifier le contenu
cat .env

# 3. Créer les dossiers nécessaires
mkdir -p data/bronze data/silver data/gold data/quality_reports
mkdir -p logs backups
```

**Résultat attendu:**
- Fichier `.env` créé avec les variables de config
- Dossiers `data/`, `logs/`, `backups/` créés

---

### Phase 3: Build des Images (5-10 min)

```bash
# Construction des images Docker
docker-compose build

# Vérifier les images créées
docker images | grep off
```

**Résultat attendu:**
```
off_etl        latest    xxx    xxx ago    1.2GB
```

**Si erreur de build:**
```bash
# Rebuild sans cache
docker-compose build --no-cache

# Voir les logs détaillés
docker-compose build --progress=plain
```

---

### Phase 4: Démarrage des Services (1 min)

```bash
# Démarrer MySQL + ETL
docker-compose up -d mysql etl

# Attendre 30 secondes que MySQL démarre
# Puis vérifier l'état
docker-compose ps
```

**Résultat attendu:**
```
NAME        IMAGE       STATUS              PORTS
off_mysql   mysql:8.0   Up 30 seconds      0.0.0.0:3306->3306/tcp
off_etl     ...         Up 30 seconds
```

**Si services ne démarrent pas:**
```bash
# Voir les logs
docker-compose logs mysql
docker-compose logs etl
```

---

### Phase 5: Test de Connexion (1 min)

```bash
# Test 1: MySQL est accessible
docker-compose exec mysql mysqladmin ping -h localhost -u root -ppassword

# Test 2: Base de données existe
docker-compose exec mysql mysql -u root -ppassword -e "SHOW DATABASES;"

# Test 3: Tables créées
docker-compose exec mysql mysql -u root -ppassword off_datamart -e "SHOW TABLES;"
```

**Résultat attendu:**
```
mysqld is alive

DATABASES:
off_datamart

TABLES:
dim_brand
dim_category
dim_country
dim_product
dim_time
fact_nutrition_snapshot
```

---

### Phase 6: Test ETL avec Données Échantillon (2-3 min)

```bash
# Exécuter le pipeline complet avec données de test
docker-compose exec etl python -m etl.main tests/sample_data.jsonl

# Ou avec Make (si disponible)
make etl-test
```

**Résultat attendu:**
```
================================================================================
STARTING FULL ETL PIPELINE
================================================================================
Start time: 2024-01-XX XX:XX:XX
Input path: tests/sample_data.jsonl
================================================================================

[1/6] Running Bronze Ingestion...
✓ Ingested X records

[2/6] Running Silver Conformation...
✓ Processed X records

[3/6] Loading Dimensions...
✓ Loaded dimensions

[4/6] Loading Products (SCD2)...
✓ Loaded X products

[5/6] Loading Fact Table...
✓ Loaded X facts

[6/6] Generating Quality Report...
✓ Report generated

================================================================================
ETL PIPELINE COMPLETED SUCCESSFULLY
================================================================================
Duration: XX.XX seconds
================================================================================
```

**Si erreur:**
```bash
# Voir les logs détaillés
docker-compose logs etl

# Vérifier la connexion DB
docker-compose exec etl python -c "from etl.settings import DB_CONFIG; print(DB_CONFIG)"
```

---

### Phase 7: Vérification des Résultats (2 min)

```bash
# 1. Ouvrir la console MySQL
docker-compose exec mysql mysql -u root -ppassword off_datamart
```

```sql
-- Dans MySQL, exécuter ces requêtes:

-- Compter les produits
SELECT COUNT(*) as total_products FROM dim_product WHERE is_current = 1;

-- Compter les faits
SELECT COUNT(*) as total_facts FROM fact_nutrition_snapshot;

-- Voir la distribution Nutri-Score
SELECT
    nutriscore_grade,
    COUNT(*) as count
FROM fact_nutrition_snapshot
GROUP BY nutriscore_grade
ORDER BY nutriscore_grade;

-- Top 5 marques
SELECT
    b.brand_name,
    COUNT(*) as product_count
FROM dim_brand b
JOIN dim_product p ON b.brand_sk = p.brand_sk
WHERE p.is_current = 1
GROUP BY b.brand_name
ORDER BY product_count DESC
LIMIT 5;

-- Sortir de MySQL
exit
```

**Résultat attendu:**
- Plusieurs produits dans `dim_product`
- Données dans `fact_nutrition_snapshot`
- Distribution des Nutri-Scores (a, b, c, d, e)
- Liste des marques

---

### Phase 8: Vérifier le Rapport Qualité (1 min)

```bash
# Voir le rapport qualité généré
cat data/quality_reports/quality_report_*.json

# Ou avec formatage
cat data/quality_reports/quality_report_*.json | python -m json.tool
```

**Résultat attendu:**
```json
{
  "execution_timestamp": "2024-01-XX...",
  "total_records": XX,
  "completeness": {
    "average_score": 0.XX,
    "distribution": {...}
  },
  "anomalies": {
    "out_of_bounds": XX,
    "missing_required": XX
  },
  "alerts": [...]
}
```

---

### Phase 9: Tests Unitaires (1 min)

```bash
# Exécuter les tests
docker-compose exec etl pytest tests/test_etl.py -v

# Ou avec Make
make test
```

**Résultat attendu:**
```
tests/test_etl.py::TestUtils::test_normalize_tag PASSED
tests/test_etl.py::TestUtils::test_convert_sodium_to_salt PASSED
tests/test_etl.py::TestQualityRules::test_check_bounds PASSED
...
======================== X passed in X.XXs ========================
```

---

### Phase 10: Test Jupyter (Optionnel - 1 min)

```bash
# Démarrer Jupyter
docker-compose up -d jupyter

# Attendre 10 secondes
# Ouvrir dans le navigateur
start http://localhost:8888

# Ou sur Linux/Mac
open http://localhost:8888
```

**Résultat attendu:**
- Jupyter Lab s'ouvre dans le navigateur
- Accès au notebook `projet/OpenFoodFacts_ETL_Workshop.ipynb`

---

## 🎯 Tests Avancés (Optionnel)

### Test avec Dataset Complet

```bash
# 1. Télécharger le dataset (~5GB, ~30 min)
docker-compose exec etl python download_dump.py

# 2. Exécuter le pipeline complet (~10-30 min selon machine)
docker-compose exec etl python -m etl.main data/openfoodfacts-products.jsonl

# 3. Vérifier les résultats
docker-compose exec mysql mysql -u root -ppassword off_datamart -e "
SELECT COUNT(*) as total FROM fact_nutrition_snapshot;
"
```

### Test Incrémental

```bash
# 1. Premier run
docker-compose exec etl python -m etl.main tests/sample_data.jsonl

# 2. Deuxième run (devrait détecter les doublons)
docker-compose exec etl python -m etl.main tests/sample_data.jsonl

# 3. Run avec skip ingestion (réutiliser Bronze)
docker-compose exec etl python -m etl.main --skip-ingest
```

---

## 🆘 Troubleshooting

### Problème: Port 3306 déjà utilisé

```bash
# Solution 1: Arrêter le MySQL local
# Windows: Services → MySQL → Stop
# Linux: sudo service mysql stop

# Solution 2: Changer le port
echo "DB_PORT=3307" >> .env
docker-compose down
docker-compose up -d
```

### Problème: Erreur mémoire Spark

```bash
# Augmenter la mémoire
echo "SPARK_DRIVER_MEMORY=4g" >> .env
docker-compose restart etl
```

### Problème: Erreur MySQL "Access Denied"

```bash
# Vérifier les credentials
docker-compose exec etl env | grep DB_

# Réinitialiser MySQL
docker-compose down
docker volume rm off_mysql_data
docker-compose up -d mysql
# Attendre 30 secondes
```

### Problème: Conteneur crashe au démarrage

```bash
# Voir les logs
docker-compose logs --tail=50 etl
docker-compose logs --tail=50 mysql

# Reconstruire l'image
docker-compose build --no-cache etl
docker-compose up -d
```

---

## 📊 Checklist Finale

Avant de considérer le projet validé, vérifier:

- [ ] Docker et Docker Compose installés
- [ ] Images Docker buildées sans erreur
- [ ] Services MySQL et ETL démarrent
- [ ] Connexion MySQL fonctionne
- [ ] Tables créées dans la base
- [ ] ETL s'exécute sans erreur
- [ ] Données chargées dans MySQL
- [ ] Rapport qualité généré
- [ ] Tests unitaires passent
- [ ] Jupyter accessible (optionnel)

---

## 🎓 Pour le Rendu

```bash
# 1. Démonstration complète
docker-compose build
docker-compose up -d
docker-compose exec etl python -m etl.main tests/sample_data.jsonl

# 2. Capturer les résultats
docker-compose logs etl > rendu/logs_execution.txt
cat data/quality_reports/quality_report_*.json > rendu/qualite.json
docker-compose exec mysql mysql -u root -ppassword off_datamart < sql/analysis_queries.sql > rendu/sql_results.txt

# 3. Screenshots
# - Exécution du pipeline
# - Résultats dans MySQL
# - Rapport qualité
```

---

## 📞 Aide

**Si blocage:**
1. Consulter les logs: `docker-compose logs`
2. Vérifier QUICKSTART.md
3. Vérifier DOCKER_README.md
4. Reconstruire: `docker-compose build --no-cache`

**Tout réinitialiser:**
```bash
docker-compose down -v
docker system prune -a
rm -rf data/bronze data/silver data/gold
# Puis refaire: docker-compose build && docker-compose up -d
```

---

**Temps total de test: ~15-20 minutes**
**Temps avec dataset complet: ~1-2 heures**
