"""
ETL Configuration Settings
M1 EISI/CDPIA/CYBER - Atelier Intégration des Données
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONF_DIR = BASE_DIR / "conf"

# Data Lake paths (Medallion Architecture)
BRONZE_PATH = str(DATA_DIR / "bronze")
SILVER_PATH = str(DATA_DIR / "silver")
GOLD_PATH = str(DATA_DIR / "gold")

# MySQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "off_datamart"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

# JDBC Configuration
JDBC_URL = f"jdbc:mysql://{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
JDBC_PROPERTIES = {
    "user": DB_CONFIG["user"],
    "password": DB_CONFIG["password"],
    "driver": "com.mysql.cj.jdbc.Driver",
}

# Quality Rules Configuration
QUALITY_RULES = {
    "nutriments": {
        "energy_kcal_100g": {"min": 0, "max": 900},
        "sugars_100g": {"min": 0, "max": 100},
        "fat_100g": {"min": 0, "max": 100},
        "saturated_fat_100g": {"min": 0, "max": 100},
        "salt_100g": {"min": 0, "max": 25},
        "sodium_100g": {"min": 0, "max": 10},
        "proteins_100g": {"min": 0, "max": 100},
        "fiber_100g": {"min": 0, "max": 100},
    },
    "completeness_weights": {
        "product_name": 0.2,
        "brands": 0.15,
        "categories": 0.15,
        "nutriscore_grade": 0.1,
        "energy_kcal_100g": 0.1,
        "sugars_100g": 0.075,
        "fat_100g": 0.075,
        "saturated_fat_100g": 0.05,
        "salt_100g": 0.05,
        "proteins_100g": 0.075,
        "fiber_100g": 0.05,
    },
    "alerts": {
        "completeness_threshold": 0.5,
        "anomaly_threshold": 100,
    }
}

# Spark Configuration
SPARK_CONFIG = {
    "spark.sql.session.timeZone": "UTC",
    "spark.jars.packages": "com.mysql:mysql-connector-j:8.0.33",
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.adaptive.coalescePartitions.enabled": "true",
}

# OpenFoodFacts API Configuration
OFF_API_BASE_URL = "https://world.openfoodfacts.org/api/v2"
OFF_EXPORT_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"

# ETL Run Metadata
RUN_METADATA_PATH = str(DATA_DIR / "run_metadata.json")
