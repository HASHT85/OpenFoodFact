"""
Gold Layer - Load Dimensions Job
Loads small dimensions (brand, category, country, time) into MySQL
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from datetime import datetime, timedelta

from etl.utils import setup_logger
from etl.settings import SILVER_PATH, JDBC_URL, JDBC_PROPERTIES


logger = setup_logger("LoadDimensions")


def load_dim_brand(spark: SparkSession, df_silver: DataFrame) -> dict:
    """
    Load dim_brand dimension table
    Strategy: Insert new brands only (no updates needed)
    """
    logger.info("Loading dim_brand...")

    # Extract distinct brands from Silver
    brands_new = (df_silver
                  .select("brands")
                  .filter(F.col("brands").isNotNull())
                  .distinct()
                  .withColumnRenamed("brands", "brand_name"))

    new_count = brands_new.count()
    logger.info(f"Found {new_count} distinct brands in Silver")

    try:
        # Read existing brands from MySQL
        existing_brands = spark.read.jdbc(
            JDBC_URL,
            "dim_brand",
            properties=JDBC_PROPERTIES
        ).select("brand_name")

        # Find truly new brands (left anti join)
        truly_new_brands = brands_new.join(
            existing_brands,
            on="brand_name",
            how="left_anti"
        )

        insert_count = truly_new_brands.count()

        if insert_count > 0:
            logger.info(f"Inserting {insert_count} new brands...")
            truly_new_brands.write.jdbc(
                JDBC_URL,
                "dim_brand",
                mode="append",
                properties=JDBC_PROPERTIES
            )
        else:
            logger.info("No new brands to insert")

    except Exception as e:
        # First load: table might be empty
        logger.warning(f"Could not read existing brands (first load?): {e}")
        logger.info(f"Inserting all {new_count} brands...")
        brands_new.write.jdbc(
            JDBC_URL,
            "dim_brand",
            mode="append",
            properties=JDBC_PROPERTIES
        )
        insert_count = new_count

    return {"dimension": "dim_brand", "inserted": insert_count}


def load_dim_category(spark: SparkSession, df_silver: DataFrame) -> dict:
    """
    Load dim_category dimension table
    Simplified: just load unique categories without hierarchy (can be enhanced)
    """
    logger.info("Loading dim_category...")

    # Explode categories array to get all unique categories
    categories_exploded = (df_silver
                          .select(F.explode("categories_normalized").alias("category_code"))
                          .filter(F.col("category_code").isNotNull())
                          .distinct())

    # Add basic structure (simplified, no hierarchy parsing in this version)
    categories_new = (categories_exploded
                     .withColumn("category_name_fr", F.col("category_code"))
                     .withColumn("level", F.lit(1))
                     .withColumn("parent_category_sk", F.lit(None).cast("int")))

    new_count = categories_new.count()
    logger.info(f"Found {new_count} distinct categories")

    try:
        existing_categories = spark.read.jdbc(
            JDBC_URL,
            "dim_category",
            properties=JDBC_PROPERTIES
        ).select("category_code")

        truly_new_categories = categories_new.join(
            existing_categories,
            on="category_code",
            how="left_anti"
        )

        insert_count = truly_new_categories.count()

        if insert_count > 0:
            logger.info(f"Inserting {insert_count} new categories...")
            truly_new_categories.write.jdbc(
                JDBC_URL,
                "dim_category",
                mode="append",
                properties=JDBC_PROPERTIES
            )
        else:
            logger.info("No new categories to insert")

    except Exception as e:
        logger.warning(f"Could not read existing categories: {e}")
        logger.info(f"Inserting all {new_count} categories...")
        categories_new.write.jdbc(
            JDBC_URL,
            "dim_category",
            mode="append",
            properties=JDBC_PROPERTIES
        )
        insert_count = new_count

    return {"dimension": "dim_category", "inserted": insert_count}


def load_dim_country(spark: SparkSession, df_silver: DataFrame) -> dict:
    """
    Load dim_country dimension table
    """
    logger.info("Loading dim_country...")

    # Explode countries array
    countries_exploded = (df_silver
                         .select(F.explode("countries_normalized").alias("country_code"))
                         .filter(F.col("country_code").isNotNull())
                         .distinct())

    # Add country name (simplified: same as code, can be enhanced with mapping)
    countries_new = (countries_exploded
                    .withColumn("country_name_fr", F.col("country_code")))

    new_count = countries_new.count()
    logger.info(f"Found {new_count} distinct countries")

    try:
        existing_countries = spark.read.jdbc(
            JDBC_URL,
            "dim_country",
            properties=JDBC_PROPERTIES
        ).select("country_code")

        truly_new_countries = countries_new.join(
            existing_countries,
            on="country_code",
            how="left_anti"
        )

        insert_count = truly_new_countries.count()

        if insert_count > 0:
            logger.info(f"Inserting {insert_count} new countries...")
            truly_new_countries.write.jdbc(
                JDBC_URL,
                "dim_country",
                mode="append",
                properties=JDBC_PROPERTIES
            )
        else:
            logger.info("No new countries to insert")

    except Exception as e:
        logger.warning(f"Could not read existing countries: {e}")
        logger.info(f"Inserting all {new_count} countries...")
        countries_new.write.jdbc(
            JDBC_URL,
            "dim_country",
            mode="append",
            properties=JDBC_PROPERTIES
        )
        insert_count = new_count

    return {"dimension": "dim_country", "inserted": insert_count}


def load_dim_time(spark: SparkSession, start_date: str = "2020-01-01", end_date: str = "2030-12-31") -> dict:
    """
    Load or populate dim_time dimension table
    Pre-populate time dimension for the specified date range

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    logger.info(f"Loading dim_time from {start_date} to {end_date}...")

    # Check if dim_time already has data
    try:
        existing_count = spark.read.jdbc(
            JDBC_URL,
            "dim_time",
            properties=JDBC_PROPERTIES
        ).count()

        if existing_count > 0:
            logger.info(f"dim_time already populated with {existing_count} records. Skipping.")
            return {"dimension": "dim_time", "inserted": 0, "existing": existing_count}
    except Exception:
        logger.info("dim_time is empty, will populate...")

    # Generate date range
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    dates_list = []
    current = start

    while current <= end:
        time_sk = int(current.strftime("%Y%m%d"))
        dates_list.append({
            "time_sk": time_sk,
            "date": current.strftime("%Y-%m-%d"),
            "year": current.year,
            "month": current.month,
            "day": current.day,
            "week": current.isocalendar()[1],
            "iso_week": current.isocalendar()[1]
        })
        current += timedelta(days=1)

    logger.info(f"Generated {len(dates_list)} date records")

    # Create DataFrame and write to MySQL
    df_time = spark.createDataFrame(dates_list)

    df_time.write.jdbc(
        JDBC_URL,
        "dim_time",
        mode="append",
        properties=JDBC_PROPERTIES
    )

    logger.info(f"dim_time loaded with {len(dates_list)} records")

    return {"dimension": "dim_time", "inserted": len(dates_list)}


def run_load_dimensions_job(spark: SparkSession) -> dict:
    """
    Main entry point for dimensions loading job

    Returns:
        Dictionary with job metrics
    """
    logger.info("=" * 80)
    logger.info("GOLD LAYER - LOAD DIMENSIONS JOB")
    logger.info("=" * 80)

    # Read Silver layer
    logger.info(f"Reading Silver layer from: {SILVER_PATH}")
    df_silver = spark.read.parquet(SILVER_PATH)

    results = []

    # Load each dimension
    results.append(load_dim_brand(spark, df_silver))
    results.append(load_dim_category(spark, df_silver))
    results.append(load_dim_country(spark, df_silver))
    results.append(load_dim_time(spark))

    metrics = {
        "job": "load_dimensions",
        "layer": "gold",
        "dimensions_loaded": results
    }

    logger.info("=" * 80)
    logger.info("Dimension loading complete:")
    for result in results:
        logger.info(f"  {result['dimension']}: {result.get('inserted', 0)} records inserted")
    logger.info("=" * 80)

    return metrics


if __name__ == "__main__":
    from etl.utils import create_spark_session

    spark = create_spark_session("OFF_Load_Dimensions")

    try:
        metrics = run_load_dimensions_job(spark)
        print("\n✓ Dimensions loading completed successfully")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()
