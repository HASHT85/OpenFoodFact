import os

# Project Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # etl/
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Data Paths
# In a real scenario, these might point to S3 or HDFS
DATA_DIR = os.path.join(PROJECT_ROOT, "data") # Local simulation
BRONZE_DIR = os.path.join(DATA_DIR, "bronze")
SILVER_DIR = os.path.join(DATA_DIR, "silver")
GOLD_DIR = os.path.join(DATA_DIR, "gold") # Not strictly used if loading to MySQL, but good for intermediate

# Database Configuration (MySQL)
# Default to environment variables or fallback to defaults
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "off_datamart")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

DB_PROPS = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "driver": "com.mysql.cj.jdbc.Driver"
}

JDBC_URL = f"jdbc:mysql://{DB_HOST}:{DB_PORT}/{DB_NAME}?allowPublicKeyRetrieval=true&useSSL=false"

# Spark Config
SPARK_APP_NAME = "OFF_Etl_Pipeline"
