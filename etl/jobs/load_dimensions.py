import sys
import os
from pyspark.sql import functions as F

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_spark_session, get_logger

def load_simple_dimensions(spark, silver_path, db_props, jdbc_url):
    logger = get_logger("GoldDimLoader")
    df = spark.read.parquet(silver_path)

    # 1. Dim Brand
    # Extract unique brands, ignore nulls
    brands = df.select("brands").where(F.col("brands").isNotNull()) \
               .distinct() \
               .withColumnRenamed("brands", "brand_name")
    
    # Write to MySQL (Insert Ignore mostly handled by JDBC options or we use a specific query)
    # Spark JDBC 'append' will fail on duplicate PRIMARY/UNIQUE keys unless we handle it.
    # For now, we will use 'INSERT IGNORE' via a custom writer or just assume clean starts for the workshop.
    # A robust way is to read existing brands, diff, and write new ones.
    
    # Simplified strategy: READ existing -> LEFT ANTI DATA -> WRITE NEW
    existing_brands = spark.read.jdbc(jdbc_url, "dim_brand", properties=db_props)
    new_brands = brands.join(existing_brands, on="brand_name", how="left_anti")
    
    if new_brands.count() > 0:
        new_brands.write.jdbc(jdbc_url, "dim_brand", mode="append", properties=db_props)
        logger.info(f"Inserted {new_brands.count()} new brands.")
    
    # 2. Dim Country (Explode countries tags)
    # silver has countries_normalized as Array
    countries = df.select(F.explode("countries_normalized").alias("country_code")) \
                  .distinct()
    
    existing_countries = spark.read.jdbc(jdbc_url, "dim_country", properties=db_props)
    new_countries = countries.join(existing_countries, on="country_code", how="left_anti")
    
    if new_countries.count() > 0:
        new_countries.write.jdbc(jdbc_url, "dim_country", mode="append", properties=db_props)
        logger.info(f"Inserted {new_countries.count()} new countries.")

    # 3. Dim Category (Explode categories tags)
    categories = df.select(F.explode("categories_normalized").alias("category_code")) \
                   .distinct()
                   
    existing_categories = spark.read.jdbc(jdbc_url, "dim_category", properties=db_props)
    new_categories = categories.join(existing_categories, on="category_code", how="left_anti")
    
    if new_categories.count() > 0:
        new_categories.write.jdbc(jdbc_url, "dim_category", mode="append", properties=db_props)
        logger.info(f"Inserted {new_categories.count()} new categories.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: load_dimensions.py <silver_parquet_path>")
        sys.exit(1)

    silver_path = sys.argv[1]
    
    # Import settings
    import settings
    
    spark = get_spark_session("OFF_Gold_Dims")
    
    # Use settings for connection
    load_simple_dimensions(spark, silver_path, settings.DB_PROPS, settings.JDBC_URL)
    
    spark.stop()
