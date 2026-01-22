import sys
import os
from pyspark.sql import functions as F
from pyspark.sql import Window

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_spark_session, get_logger

def conform_data(spark, input_path, output_path):
    logger = get_logger("SilverConformation")
    logger.info(f"Starting conformation from {input_path}")

    df = spark.read.parquet(input_path)

    # 1. Deduplication (Window by code, order by last_modified_t desc)
    # We filter for row_number = 1
    window_spec = Window.partitionBy("code").orderBy(F.col("last_modified_t").desc())
    
    df_dedup = df.withColumn("rn", F.row_number().over(window_spec)) \
                 .filter(F.col("rn") == 1) \
                 .drop("rn")

    logger.info(f"Deduplication complete. Input count: {df.count()}, Output count: {df_dedup.count()}")

    # 2. Normalization / Cleaning
    # - Trim strings
    # - Handle empty strings as nulls?
    # - Flatten simple tags (e.g. remove "en:" prefix if desirable, or just explode later)
    
    # Example: Normalize country tags (remove "en:" prefix)
    # Define a UDF or use SQL expression? SQL expression is faster.
    # We will use transform function for arrays (Spark 2.4+)
    
    # transform(countries_tags, x -> regexp_replace(x, '^..:', ''))
    
    df_cleaned = df_dedup.withColumn("countries_normalized", F.expr("transform(countries_tags, x -> regexp_replace(x, '^..:', ''))")) \
                         .withColumn("categories_normalized", F.expr("transform(categories_tags, x -> regexp_replace(x, '^..:', ''))"))

    # 3. Type Casting & Unit Harmonization (Example: salt vs sodium)
    # If salt is null and sodium is present: salt = sodium * 2.5
    df_enriched = df_cleaned.withColumn(
        "nutriments.salt_100g", 
        F.coalesce(F.col("nutriments.salt_100g"), F.col("nutriments.sodium_100g") * 2.5)
    )

    # Write Silver
    df_enriched.write.mode("overwrite").parquet(output_path)
    logger.info("Silver conformation complete.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: conform.py <input_parquet_path> <output_parquet_path>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    spark = get_spark_session("OFF_Silver_Conformation")
    conform_data(spark, input_path, output_path)
    spark.stop()
