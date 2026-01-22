import sys
import os
from pyspark.sql import functions as F

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_spark_session, get_logger

def load_products_scd(spark, silver_path, db_props, jdbc_url):
    logger = get_logger("GoldProductSCD")
    
    # 1. Read Incoming and Calculate Hash
    df_silver = spark.read.parquet(silver_path)
    
    # Define columns to track for changes
    track_cols = ["product_name", "brands", "categories_tags", "countries_tags", "nutriscore_grade"]
    # We need to ensure we use the same columns for hashing always
    
    # Add Hash Column
    # Concat columns logic
    # We cast everything to string and concat
    concat_expr = F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in track_cols])
    df_input = df_silver.withColumn("row_hash", F.md5(concat_expr))
    
    # 2. Read Active Products from MySQL
    query_active = "SELECT product_sk, code, row_hash as current_hash FROM dim_product WHERE is_current = 1"
    df_active = spark.read.jdbc(jdbc_url, table=f"({query_active}) as t", properties=db_props)
    
    # 3. Join to detect changes
    # code is the natural key
    df_joined = df_input.join(df_active, "code", "left")
    
    # New Records: code is null in df_active
    df_new = df_joined.filter(F.col("product_sk").isNull())
    
    # Changed Records: code exists AND hash differs
    df_changed = df_joined.filter(
        F.col("product_sk").isNotNull() & (F.col("row_hash") != F.col("current_hash"))
    )
    
    # Unchanged: code exists AND hash matches (Ignore)
    
    count_new = df_new.count()
    count_changed = df_changed.count()
    logger.info(f"Detected {count_new} new products and {count_changed} changed products.")
    
    if count_new == 0 and count_changed == 0:
        logger.info("No changes to apply.")
        return

    # 4. Prepare Updates (expire old records)
    if count_changed > 0:
        # We need to expire the product_sk found in df_changed
        ids_to_expire = df_changed.select("product_sk")
        
        # Write to temporary table in MySQL
        ids_to_expire.write.jdbc(jdbc_url, "tmp_expire_products", mode="overwrite", properties=db_props)
        
        # Execute UPDATE via a separate connection (or JDBC Hook if possible)
        # Here we simulate the logic. In PySpark valid generic way is limited.
        # We assume the user has a way to run the SQL or we can try to use a specialized driver call.
        # For this file, we will document that the SQL needs to be run.
        logger.warning("IMPORTANT: Run SQL to expire records using 'tmp_expire_products' join.")
        # "UPDATE dim_product p JOIN tmp_expire_products t ON p.product_sk = t.product_sk SET p.is_current = 0, p.effective_to = NOW()"
        
        # In a real pipeline, we'd use a python DB driver (mysql-connector) here:
        import mysql.connector
        import settings # Import settings here since it's available via sys.path
        try:
            conn = mysql.connector.connect(
                user=db_props["user"], 
                password=db_props["password"],
                host=settings.DB_HOST,
                port=int(settings.DB_PORT),
                database=settings.DB_NAME
            )
            cursor = conn.cursor()
            update_sql = """
            UPDATE dim_product p 
            JOIN tmp_expire_products t ON p.product_sk = t.product_sk 
            SET p.is_current = 0, p.effective_to = NOW()
            """
            cursor.execute(update_sql)
            conn.commit()
            logger.info("Expired old product versions in MySQL.")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update MySQL: {e}")

    # 5. Prepare Inserts (New + Changed are both new rows)
    # We need to map columns to target schema
    # dim_product columns: code, product_name, brand_sk, primary_category_sk, ...
    
    # Resolving FKs (brand_sk, category_sk) is needed before insert.
    # This requires looking up dim_brand and dim_category.
    # For performance, broadcast join if dims are small.
    
    df_brand = spark.read.jdbc(jdbc_url, "dim_brand", properties=db_props).select("brand_sk", "brand_name")
    df_cat = spark.read.jdbc(jdbc_url, "dim_category", properties=db_props).select("category_sk", F.col("category_code"))
    
    # Union New and Changed for insertion
    df_to_insert = df_new.unionByName(df_changed, allowMissingColumns=True)
    
    # Join FKs
    df_final = df_to_insert \
        .join(df_brand, df_to_insert.brands == df_brand.brand_name, "left") \
        .join(df_cat, F.expr("categories_normalized[0]") == df_cat.category_code, "left") \
        .select(
            F.col("code"),
            F.col("product_name"),
            F.col("brand_sk"),
            F.col("brands").alias("brand_name_normalized"),
            F.col("category_sk").alias("primary_category_sk"),
            F.col("countries_normalized").cast("string").alias("countries_multi"), # Save as JSON string
            F.lit(1).alias("is_current"),
            F.current_timestamp().alias("effective_from"),
            F.lit(None).cast("timestamp").alias("effective_to"),
            F.col("row_hash")
        )

    # Write
    df_final.write.jdbc(jdbc_url, "dim_product", mode="append", properties=db_props)
    logger.info(f"Inserted {df_final.count()} active product records.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: load_products_scd.py <silver_parquet_path>")
        sys.exit(1)

    silver_path = sys.argv[1]
    
    # Import settings
    import settings
    
    # Use settings
    spark = get_spark_session("OFF_Gold_SCD")
    load_products_scd(spark, silver_path, settings.DB_PROPS, settings.JDBC_URL)
    spark.stop()
