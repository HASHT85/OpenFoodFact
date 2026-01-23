"""
Gold Layer - Load Fact Table
Loads fact_nutrition_snapshot with nutritional measures and quality metrics
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from datetime import datetime

from etl.utils import setup_logger, collect_quality_issues
from etl.settings import SILVER_PATH, JDBC_URL, JDBC_PROPERTIES


logger = setup_logger("LoadFact")


def get_product_mapping(spark: SparkSession) -> DataFrame:
    """
    Get code -> product_sk mapping for active products
    """
    query = "(SELECT product_sk, code FROM dim_product WHERE is_current = 1) AS active_products"
    return spark.read.jdbc(
        JDBC_URL,
        query,
        properties=JDBC_PROPERTIES
    )


def get_time_sk_for_date(date_str: str) -> int:
    """
    Convert date string to time_sk (YYYYMMDD format)

    Args:
        date_str: Date in any format

    Returns:
        time_sk as integer
    """
    # For this workshop, use current date
    # In production, would parse last_modified_t
    return int(datetime.now().strftime("%Y%m%d"))


def prepare_fact_data(df_silver: DataFrame, product_mapping: DataFrame) -> DataFrame:
    """
    Prepare fact table data from Silver with proper foreign keys

    Args:
        df_silver: Silver layer DataFrame
        product_mapping: Product SK mapping

    Returns:
        DataFrame ready for fact table insertion
    """
    logger.info("Preparing fact data...")

    # Join with product mapping to get product_sk
    df = df_silver.join(
        product_mapping,
        on="code",
        how="inner"  # Only include products that exist in dim_product
    )

    # Compute time_sk from last_modified_t
    # Convert Unix timestamp to date and then to time_sk (YYYYMMDD)
    df = df.withColumn(
        "time_sk",
        F.from_unixtime(F.col("last_modified_t"), "yyyyMMdd").cast("int")
    )

    # Collect quality issues into JSON
    issue_columns = [
        "energy_kcal_100g_out_of_bounds",
        "sugars_100g_out_of_bounds",
        "fat_100g_out_of_bounds",
        "saturated_fat_100g_out_of_bounds",
        "salt_100g_out_of_bounds",
        "sodium_100g_out_of_bounds",
        "proteins_100g_out_of_bounds",
        "fiber_100g_out_of_bounds"
    ]

    df = collect_quality_issues(df, issue_columns)

    # Select columns for fact table
    df_fact = df.select(
        F.col("product_sk"),
        F.col("time_sk"),
        # Measures (100g)
        F.col("energy_kcal_100g"),
        F.col("fat_100g"),
        F.col("saturated_fat_100g"),
        F.col("sugars_100g"),
        F.col("salt_100g"),
        F.col("proteins_100g"),
        F.col("fiber_100g"),
        F.col("sodium_100g"),
        # Scores & Attributes
        F.col("nutriscore_grade"),
        F.col("nova_group"),
        F.col("ecoscore_grade"),
        # Quality Metrics
        F.col("completeness_score"),
        F.col("quality_issues_json")
    )

    return df_fact


def load_fact_nutrition(spark: SparkSession, df_fact: DataFrame) -> dict:
    """
    Load fact_nutrition_snapshot table

    Strategy: Append-only (no updates)
    Each ETL run adds new snapshots

    Returns:
        Dictionary with metrics
    """
    logger.info("Loading fact_nutrition_snapshot...")

    total_records = df_fact.count()
    logger.info(f"Inserting {total_records} fact records...")

    # Write to MySQL
    # Use append mode since facts are immutable snapshots
    df_fact.write.jdbc(
        JDBC_URL,
        "fact_nutrition_snapshot",
        mode="append",
        properties=JDBC_PROPERTIES
    )

    logger.info(f"Successfully loaded {total_records} fact records")

    # Collect quality metrics
    records_with_issues = df_fact.filter(
        F.col("quality_issues_json") != "{}"
    ).count()

    avg_completeness = df_fact.agg(
        F.avg("completeness_score")
    ).collect()[0][0]

    return {
        "total_records": total_records,
        "records_with_quality_issues": records_with_issues,
        "avg_completeness": round(float(avg_completeness), 3) if avg_completeness else 0
    }


def run_load_fact_job(spark: SparkSession) -> dict:
    """
    Main entry point for fact loading job

    Returns:
        Dictionary with job metrics
    """
    logger.info("=" * 80)
    logger.info("GOLD LAYER - LOAD FACT NUTRITION SNAPSHOT JOB")
    logger.info("=" * 80)

    # Read Silver layer
    logger.info(f"Reading Silver layer from: {SILVER_PATH}")
    df_silver = spark.read.parquet(SILVER_PATH)

    # Get product mapping
    product_mapping = get_product_mapping(spark)
    logger.info(f"Found {product_mapping.count()} active products")

    # Prepare fact data
    df_fact = prepare_fact_data(df_silver, product_mapping)

    # Load fact table
    result = load_fact_nutrition(spark, df_fact)

    metrics = {
        "job": "load_fact",
        "layer": "gold",
        **result
    }

    logger.info("=" * 80)
    logger.info("Fact loading complete:")
    logger.info(f"  Total records: {result['total_records']}")
    logger.info(f"  Records with issues: {result['records_with_quality_issues']}")
    logger.info(f"  Avg completeness: {result['avg_completeness']}")
    logger.info("=" * 80)

    return metrics


if __name__ == "__main__":
    from etl.utils import create_spark_session

    spark = create_spark_session("OFF_Load_Fact")

    try:
        metrics = run_load_fact_job(spark)
        print("\n✓ Fact loading completed successfully")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()
