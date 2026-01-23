"""
Bronze Layer Ingestion Job
Reads raw OpenFoodFacts data (JSON/JSONL) and writes to Parquet with explicit schema
"""
from pyspark.sql import SparkSession, DataFrame
from etl.utils import setup_logger
from etl.schema_bronze import get_bronze_schema
from etl.settings import BRONZE_PATH


logger = setup_logger("Ingest")


def ingest_raw_data(spark: SparkSession, input_path: str, output_path: str = BRONZE_PATH) -> DataFrame:
    """
    Ingest raw OpenFoodFacts data into Bronze layer

    Args:
        spark: SparkSession
        input_path: Path to JSONL or JSON file
        output_path: Path to write Bronze Parquet files

    Returns:
        DataFrame with ingested data
    """
    logger.info(f"Starting Bronze ingestion from: {input_path}")

    # Read with explicit schema
    schema = get_bronze_schema()

    try:
        df_raw = spark.read.schema(schema).json(input_path)
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        raise

    # Basic metrics
    total_records = df_raw.count()
    logger.info(f"Total records read: {total_records}")

    # Filter out records without code (required field)
    df_valid = df_raw.filter(df_raw.code.isNotNull())
    valid_records = df_valid.count()
    invalid_records = total_records - valid_records

    if invalid_records > 0:
        logger.warning(f"Filtered out {invalid_records} records without product code")

    # Write to Bronze layer (Parquet for better performance)
    logger.info(f"Writing Bronze layer to: {output_path}")
    df_valid.write.mode("overwrite").parquet(output_path)

    logger.info(f"Bronze ingestion complete. Valid records: {valid_records}")

    return df_valid


def run_ingest_job(spark: SparkSession, input_path: str) -> dict:
    """
    Main entry point for Bronze ingestion job

    Returns:
        Dictionary with job metrics
    """
    logger.info("=" * 80)
    logger.info("BRONZE LAYER INGESTION JOB")
    logger.info("=" * 80)

    df = ingest_raw_data(spark, input_path)

    metrics = {
        "job": "ingest",
        "layer": "bronze",
        "input_path": input_path,
        "output_path": BRONZE_PATH,
        "total_records": df.count(),
    }

    logger.info(f"Ingestion metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    import sys
    from etl.utils import create_spark_session

    if len(sys.argv) < 2:
        print("Usage: python -m etl.jobs.ingest <input_path>")
        sys.exit(1)

    input_file = sys.argv[1]
    spark = create_spark_session("OFF_Bronze_Ingest")

    try:
        metrics = run_ingest_job(spark, input_file)
        print(f"\n✓ Bronze ingestion completed successfully")
        print(f"  Records: {metrics['total_records']}")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)
    finally:
        spark.stop()
