"""
Gold Layer - Load Product Dimension with SCD Type 2
Handles slowly changing dimensions for product metadata
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

from etl.utils import setup_logger
from etl.settings import SILVER_PATH, JDBC_URL, JDBC_PROPERTIES


logger = setup_logger("LoadProductSCD")


def get_brand_mapping(spark: SparkSession) -> DataFrame:
    """Get brand_name -> brand_sk mapping from MySQL"""
    return spark.read.jdbc(
        JDBC_URL,
        "dim_brand",
        properties=JDBC_PROPERTIES
    ).select("brand_sk", "brand_name")


def get_category_mapping(spark: SparkSession) -> DataFrame:
    """Get category_code -> category_sk mapping from MySQL"""
    return spark.read.jdbc(
        JDBC_URL,
        "dim_category",
        properties=JDBC_PROPERTIES
    ).select("category_sk", "category_code")


def prepare_product_input(df_silver: DataFrame, brand_mapping: DataFrame, category_mapping: DataFrame) -> DataFrame:
    """
    Prepare product data from Silver with surrogate key lookups

    Args:
        df_silver: Silver layer DataFrame
        brand_mapping: Brand SK mapping
        category_mapping: Category SK mapping

    Returns:
        DataFrame ready for SCD2 processing
    """
    logger.info("Preparing product input with surrogate key lookups...")

    # Join with brand to get brand_sk
    df = df_silver.join(
        brand_mapping,
        df_silver.brands == brand_mapping.brand_name,
        "left"
    ).drop("brand_name")

    # Join with category to get primary_category_sk
    df = df.join(
        category_mapping,
        df.primary_category == category_mapping.category_code,
        "left"
    ).drop("category_code").withColumnRenamed("category_sk", "primary_category_sk")

    # Convert countries_normalized array to JSON string for storage
    df = df.withColumn(
        "countries_multi",
        F.to_json(F.col("countries_normalized"))
    )

    # Select and rename columns for dim_product
    df_product = df.select(
        F.col("code"),
        F.col("product_name"),
        F.col("brand_sk"),
        F.col("primary_category_sk"),
        F.col("countries_multi"),
        F.col("row_hash")
    )

    return df_product


def load_product_scd2(spark: SparkSession, df_input: DataFrame) -> dict:
    """
    Load products with SCD Type 2 logic

    Logic:
    1. Read active products from MySQL (is_current = 1)
    2. Compare row_hash to detect changes
    3. For changed/new products:
       - Expire old version (is_current = 0, effective_to = now)
       - Insert new version (is_current = 1, effective_from = now)

    Returns:
        Dictionary with metrics (new, updated, unchanged)
    """
    logger.info("Loading products with SCD Type 2...")

    try:
        # Read active products from MySQL
        query = "(SELECT product_sk, code, row_hash, is_current FROM dim_product WHERE is_current = 1) AS active_products"
        df_active = spark.read.jdbc(
            JDBC_URL,
            query,
            properties=JDBC_PROPERTIES
        )

        active_count = df_active.count()
        logger.info(f"Found {active_count} active products in database")

    except Exception as e:
        logger.warning(f"Could not read active products (first load?): {e}")
        df_active = None
        active_count = 0

    if df_active is None or active_count == 0:
        # First load: insert all products as new
        logger.info("First load detected. Inserting all products as new...")

        df_new = df_input.select(
            F.col("code"),
            F.col("product_name"),
            F.col("brand_sk"),
            F.col("primary_category_sk"),
            F.col("countries_multi"),
            F.lit(1).cast("boolean").alias("is_current"),
            F.current_timestamp().alias("effective_from"),
            F.lit(None).cast("timestamp").alias("effective_to"),
            F.col("row_hash")
        )

        new_count = df_new.count()
        logger.info(f"Inserting {new_count} new products...")

        df_new.write.jdbc(
            JDBC_URL,
            "dim_product",
            mode="append",
            properties=JDBC_PROPERTIES
        )

        return {
            "new_products": new_count,
            "updated_products": 0,
            "unchanged_products": 0
        }

    # Join input with active products
    df_joined = df_input.alias("inp").join(
        df_active.alias("act"),
        F.col("inp.code") == F.col("act.code"),
        "left"
    )

    # Identify new products (no match in active)
    df_new = df_joined.filter(F.col("act.product_sk").isNull()).select(
        F.col("inp.code"),
        F.col("inp.product_name"),
        F.col("inp.brand_sk"),
        F.col("inp.primary_category_sk"),
        F.col("inp.countries_multi"),
        F.lit(1).cast("boolean").alias("is_current"),
        F.current_timestamp().alias("effective_from"),
        F.lit(None).cast("timestamp").alias("effective_to"),
        F.col("inp.row_hash")
    )

    # Identify changed products (hash mismatch)
    df_changed = df_joined.filter(
        (F.col("act.product_sk").isNotNull()) &
        (F.col("inp.row_hash") != F.col("act.row_hash"))
    )

    new_count = df_new.count()
    changed_count = df_changed.count()
    unchanged_count = df_input.count() - new_count - changed_count

    logger.info(f"Product analysis: {new_count} new, {changed_count} changed, {unchanged_count} unchanged")

    # Insert new products
    if new_count > 0:
        logger.info(f"Inserting {new_count} new products...")
        df_new.write.jdbc(
            JDBC_URL,
            "dim_product",
            mode="append",
            properties=JDBC_PROPERTIES
        )

    # Handle changed products (SCD2)
    if changed_count > 0:
        logger.info(f"Processing {changed_count} changed products with SCD2...")

        # Expire old versions (this requires UPDATE, which Spark doesn't support directly)
        # Alternative: Use a staging table + MERGE or handle via SQL script
        # For this workshop, we'll use a workaround: read all, update in Spark, write back

        # Get codes of changed products
        changed_codes = df_changed.select(F.col("inp.code")).distinct()

        # Execute UPDATE via JDBC connection (not ideal but works for workshop)
        codes_list = [row['code'] for row in changed_codes.collect()]

        if codes_list:
            logger.info(f"Expiring {len(codes_list)} old product versions...")

            # Use MySQL connector to execute UPDATE
            # Note: This is a workaround for the workshop. In production, use MERGE or staging table.
            try:
                from mysql.connector import connect

                conn = connect(
                    host=JDBC_PROPERTIES["user"],
                    user=JDBC_PROPERTIES["user"],
                    password=JDBC_PROPERTIES["password"],
                    database=JDBC_URL.split("/")[-1].split("?")[0]
                )
                cursor = conn.cursor()

                for code in codes_list:
                    update_query = f"""
                    UPDATE dim_product
                    SET is_current = 0, effective_to = NOW()
                    WHERE code = '{code}' AND is_current = 1
                    """
                    cursor.execute(update_query)

                conn.commit()
                cursor.close()
                conn.close()

                logger.info("Old versions expired successfully")

            except Exception as e:
                logger.error(f"Failed to expire old versions: {e}")
                logger.warning("Continuing with inserts anyway...")

        # Insert new versions
        df_changed_insert = df_changed.select(
            F.col("inp.code"),
            F.col("inp.product_name"),
            F.col("inp.brand_sk"),
            F.col("inp.primary_category_sk"),
            F.col("inp.countries_multi"),
            F.lit(1).cast("boolean").alias("is_current"),
            F.current_timestamp().alias("effective_from"),
            F.lit(None).cast("timestamp").alias("effective_to"),
            F.col("inp.row_hash")
        )

        df_changed_insert.write.jdbc(
            JDBC_URL,
            "dim_product",
            mode="append",
            properties=JDBC_PROPERTIES
        )

        logger.info("New versions inserted")

    return {
        "new_products": new_count,
        "updated_products": changed_count,
        "unchanged_products": unchanged_count
    }


def run_load_product_scd_job(spark: SparkSession) -> dict:
    """
    Main entry point for product SCD2 loading job

    Returns:
        Dictionary with job metrics
    """
    logger.info("=" * 80)
    logger.info("GOLD LAYER - LOAD PRODUCT SCD2 JOB")
    logger.info("=" * 80)

    # Read Silver layer
    logger.info(f"Reading Silver layer from: {SILVER_PATH}")
    df_silver = spark.read.parquet(SILVER_PATH)

    # Get mappings
    brand_mapping = get_brand_mapping(spark)
    category_mapping = get_category_mapping(spark)

    # Prepare product input
    df_product_input = prepare_product_input(df_silver, brand_mapping, category_mapping)

    # Load with SCD2
    result = load_product_scd2(spark, df_product_input)

    metrics = {
        "job": "load_product_scd",
        "layer": "gold",
        **result
    }

    logger.info("=" * 80)
    logger.info("Product SCD2 loading complete:")
    logger.info(f"  New products: {result['new_products']}")
    logger.info(f"  Updated products: {result['updated_products']}")
    logger.info(f"  Unchanged products: {result['unchanged_products']}")
    logger.info("=" * 80)

    return metrics


if __name__ == "__main__":
    from etl.utils import create_spark_session

    spark = create_spark_session("OFF_Load_Product_SCD")

    try:
        metrics = run_load_product_scd_job(spark)
        print("\n✓ Product SCD2 loading completed successfully")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()
