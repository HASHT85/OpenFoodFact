import sys
import os

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_spark_session, get_logger
from schema_bronze import get_bronze_schema

def ingest_raw_data(spark, input_path, output_path):
    logger = get_logger("BronzeIngestion")
    logger.info(f"Starting ingestion from {input_path} to {output_path}")

    schema = get_bronze_schema()

    # Read JSON
    df = spark.read.schema(schema).json(input_path)

    # Basic stats
    count = df.count()
    logger.info(f"Read {count} records.")

    # Write to Parquet (Bronze)
    # Mode overwrite for idempotency in this workshop context
    df.write.mode("overwrite").parquet(output_path)
    logger.info("Bronze ingestion complete.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: ingest.py <input_json_path> <output_parquet_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    spark = get_spark_session("OFF_Bronze_Ingestion")
    ingest_raw_data(spark, input_path, output_path)
    spark.stop()
