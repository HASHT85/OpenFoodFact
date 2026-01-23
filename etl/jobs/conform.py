"""
Silver Layer Conformation Job
Cleans, normalizes, and applies quality rules to Bronze data
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from etl.utils import (
    setup_logger,
    normalize_tags,
    compute_salt_from_sodium,
    deduplicate_by_code,
    compute_row_hash,
    check_bounds,
    compute_completeness_score,
    collect_quality_issues
)
from etl.settings import BRONZE_PATH, SILVER_PATH, QUALITY_RULES


logger = setup_logger("Conform")


def resolve_product_name(df: DataFrame) -> DataFrame:
    """
    Resolve product name with language priority: fr > en > generic > fallback
    """
    return df.withColumn(
        "product_name",
        F.coalesce(
            F.col("product_name_fr"),
            F.col("product_name_en"),
            F.col("product_name"),
            F.col("generic_name"),
            F.lit("Unknown Product")
        )
    )


def flatten_nutriments(df: DataFrame) -> DataFrame:
    """
    Flatten nested nutriments structure to top-level columns
    """
    nutriment_fields = [
        "energy-kcal_100g",
        "energy-kj_100g",
        "sugars_100g",
        "fat_100g",
        "saturated-fat_100g",
        "salt_100g",
        "sodium_100g",
        "proteins_100g",
        "fiber_100g",
        "carbohydrates_100g"
    ]

    for field in nutriment_fields:
        # Rename fields with dashes to underscores
        output_field = field.replace("-", "_")
        df = df.withColumn(output_field, F.col(f"nutriments.{field}"))

    return df.drop("nutriments")


def normalize_all_tags(df: DataFrame) -> DataFrame:
    """
    Normalize all tag arrays by removing language prefixes
    """
    tag_mappings = {
        "categories_tags": "categories_normalized",
        "countries_tags": "countries_normalized",
        "additives_tags": "additives_normalized",
        "allergens_tags": "allergens_normalized",
    }

    for input_col, output_col in tag_mappings.items():
        df = normalize_tags(df, input_col, output_col)

    return df


def extract_primary_category(df: DataFrame) -> DataFrame:
    """
    Extract the first category as primary category
    """
    return df.withColumn(
        "primary_category",
        F.when(
            F.size(F.col("categories_normalized")) > 0,
            F.col("categories_normalized")[0]
        ).otherwise(F.lit(None))
    )


def apply_quality_checks(df: DataFrame) -> DataFrame:
    """
    Apply all quality checks: bounds, completeness, issue flags
    """
    # Check bounds for all nutriments
    nutriment_rules = QUALITY_RULES["nutriments"]
    bound_check_columns = []

    for column, bounds in nutriment_rules.items():
        df = check_bounds(df, column, bounds["min"], bounds["max"])
        bound_check_columns.append(f"{column}_out_of_bounds")

    # Compute completeness score
    weights = QUALITY_RULES["completeness_weights"]
    df = compute_completeness_score(df, weights)

    # Flag if any quality issues
    df = df.withColumn(
        "has_quality_issues",
        F.array_contains(F.array(*[F.col(c) for c in bound_check_columns]), True)
    )

    return df


def conform_bronze_to_silver(spark: SparkSession) -> DataFrame:
    """
    Main transformation: Bronze → Silver

    Performs:
    1. Language resolution
    2. Flattening
    3. Normalization (tags, units)
    4. Deduplication
    5. Quality checks
    6. Hash computation for SCD2
    """
    logger.info(f"Reading Bronze layer from: {BRONZE_PATH}")
    df_bronze = spark.read.parquet(BRONZE_PATH)

    initial_count = df_bronze.count()
    logger.info(f"Bronze records: {initial_count}")

    # Step 1: Resolve product names
    logger.info("Step 1: Resolving product names...")
    df = resolve_product_name(df_bronze)

    # Step 2: Flatten nutriments
    logger.info("Step 2: Flattening nutriments...")
    df = flatten_nutriments(df)

    # Step 3: Compute salt from sodium if needed
    logger.info("Step 3: Computing salt from sodium...")
    df = df.withColumn(
        "salt_100g",
        F.coalesce(F.col("salt_100g"), F.col("sodium_100g") * 2.5)
    )

    # Step 4: Normalize tags
    logger.info("Step 4: Normalizing tags...")
    df = normalize_all_tags(df)

    # Step 5: Extract primary category
    logger.info("Step 5: Extracting primary category...")
    df = extract_primary_category(df)

    # Step 6: Deduplication (keep latest)
    logger.info("Step 6: Deduplicating by code...")
    df = deduplicate_by_code(df, "last_modified_t")
    dedup_count = df.count()
    duplicates_removed = initial_count - dedup_count
    logger.info(f"Removed {duplicates_removed} duplicates. Remaining: {dedup_count}")

    # Step 7: Apply quality checks
    logger.info("Step 7: Applying quality checks...")
    df = apply_quality_checks(df)

    # Step 8: Compute row hash for SCD2
    logger.info("Step 8: Computing row hash for SCD2...")
    track_columns = [
        "product_name",
        "brands",
        "primary_category",
        "nutriscore_grade",
        "nova_group",
        "ecoscore_grade"
    ]
    df = compute_row_hash(df, track_columns, "row_hash")

    logger.info("Silver transformation complete")
    return df


def run_conform_job(spark: SparkSession) -> dict:
    """
    Main entry point for Silver conformation job

    Returns:
        Dictionary with job metrics
    """
    logger.info("=" * 80)
    logger.info("SILVER LAYER CONFORMATION JOB")
    logger.info("=" * 80)

    df_silver = conform_bronze_to_silver(spark)

    # Write Silver layer
    logger.info(f"Writing Silver layer to: {SILVER_PATH}")
    df_silver.write.mode("overwrite").parquet(SILVER_PATH)

    # Collect metrics
    total_records = df_silver.count()
    records_with_issues = df_silver.filter(F.col("has_quality_issues")).count()
    avg_completeness = df_silver.agg(F.avg("completeness_score")).collect()[0][0]

    metrics = {
        "job": "conform",
        "layer": "silver",
        "input_path": BRONZE_PATH,
        "output_path": SILVER_PATH,
        "total_records": total_records,
        "records_with_quality_issues": records_with_issues,
        "quality_issue_rate": round(records_with_issues / total_records * 100, 2) if total_records > 0 else 0,
        "avg_completeness_score": round(float(avg_completeness), 3) if avg_completeness else 0,
    }

    logger.info(f"Conformation metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    from etl.utils import create_spark_session

    spark = create_spark_session("OFF_Silver_Conform")

    try:
        metrics = run_conform_job(spark)
        print(f"\n✓ Silver conformation completed successfully")
        print(f"  Records: {metrics['total_records']}")
        print(f"  Quality issues: {metrics['records_with_quality_issues']} ({metrics['quality_issue_rate']}%)")
        print(f"  Avg completeness: {metrics['avg_completeness_score']}")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()
