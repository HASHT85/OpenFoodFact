import sys
import os
from pyspark.sql import functions as F

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_spark_session, get_logger

def load_facts(spark, silver_path, db_props, jdbc_url):
    logger = get_logger("GoldFactLoader")
    
    df_silver = spark.read.parquet(silver_path)

    # 1. Prepare Time SK (Using last_modified_t converted to YYYYMMDD)
    # If last_modified_t is long (seconds), cast to timestamp then format
    df_with_time = df_silver.withColumn(
        "time_sk", 
        F.from_unixtime("last_modified_t", "yyyyMMdd").cast("int")
    )

    # 2. Get Product SK (Active Link)
    # We join with dim_product on code where is_current = 1
    # Note: In a true historical reload, we'd join on effective ranges.
    # Here we assume we are loading the snapshot that just became current.
    
    df_product = spark.read.jdbc(jdbc_url, "dim_product", properties=db_props) \
                      .filter("is_current = 1") \
                      .select("product_sk", "code")

    df_joined = df_with_time.join(df_product, "code", "inner")

    # 3. Calculate Quality Scores / Metrics (Example logic)
    # Completeness: (count(non-null nutriments) / total potential nutriments)
    # This is a bit complex in Spark SQL without listing all cols.
    # We'll mock a score for now or use a simple UDF.
    
    df_final = df_joined.select(
        F.col("product_sk"),
        F.col("time_sk"),
        F.col("nutriments.energy-kcal_100g").alias("energy_kcal_100g"),
        F.col("nutriments.fat_100g"),
        F.col("nutriments.saturated-fat_100g").alias("saturated_fat_100g"),
        F.col("nutriments.sugars_100g"),
        F.col("nutriments.salt_100g"),
        F.col("nutriments.proteins_100g"),
        F.col("nutriments.fiber_100g"),
        F.col("nutriments.sodium_100g"),
        F.col("nutriscore_grade"),
        F.col("nova_group"),
        F.col("ecoscore_grade"),
        
        # Calculate Completeness Score
        # Columns to check for completeness
        (
            (
                F.when(F.col("nutriments.energy-kcal_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.fat_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.saturated-fat_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.sugars_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.salt_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.proteins_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.fiber_100g").isNotNull(), 1).otherwise(0) +
                F.when(F.col("nutriments.sodium_100g").isNotNull(), 1).otherwise(0)
            ) / 8.0
        ).alias("completeness_score"),
        
        F.lit("{}").alias("quality_issues_json")  # Mocked for now, requires complex validation logic
    )

    # 4. Write
    df_final.write.jdbc(jdbc_url, "fact_nutrition_snapshot", mode="append", properties=db_props)
    logger.info(f"Loaded {df_final.count()} facts.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: load_fact.py <silver_parquet_path>")
        sys.exit(1)

    silver_path = sys.argv[1]
    
    import settings
    
    spark = get_spark_session("OFF_Gold_Facts")
    load_facts(spark, silver_path, settings.DB_PROPS, settings.JDBC_URL)
    spark.stop()
