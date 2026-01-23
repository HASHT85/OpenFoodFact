"""
Utility functions for ETL pipeline
Spark session creation, logging, and common transformations
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from etl.settings import SPARK_CONFIG, RUN_METADATA_PATH


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def create_spark_session(app_name: str = "OFF_ETL") -> SparkSession:
    """Create and configure Spark session with proper settings"""
    builder = SparkSession.builder.appName(app_name)

    # Apply configuration
    for key, value in SPARK_CONFIG.items():
        builder = builder.config(key, value)

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    logger = setup_logger("SparkSession")
    logger.info(f"Spark Session created: {app_name}")
    logger.info(f"Spark version: {spark.version}")

    return spark


def normalize_tags(df: DataFrame, tag_column: str, output_column: str = None) -> DataFrame:
    """
    Normalize OpenFoodFacts tags by removing language prefixes (en:, fr:, etc.)

    Args:
        df: Input DataFrame
        tag_column: Name of the column containing tags array
        output_column: Name for output column (default: same as input)

    Returns:
        DataFrame with normalized tags
    """
    if output_column is None:
        output_column = tag_column

    return df.withColumn(
        output_column,
        F.expr(f"transform({tag_column}, x -> regexp_replace(x, '^[a-z][a-z]:', ''))")
    )


def compute_salt_from_sodium(df: DataFrame) -> DataFrame:
    """
    Compute salt from sodium when salt is missing
    Formula: salt (g) = sodium (g) × 2.5
    """
    return df.withColumn(
        "nutriments.salt_100g",
        F.coalesce(
            F.col("nutriments.salt_100g"),
            F.col("nutriments.sodium_100g") * 2.5
        )
    )


def deduplicate_by_code(df: DataFrame, order_by: str = "last_modified_t") -> DataFrame:
    """
    Remove duplicates keeping the most recent record per product code

    Args:
        df: Input DataFrame with 'code' column
        order_by: Column to use for ordering (default: last_modified_t)

    Returns:
        Deduplicated DataFrame
    """
    from pyspark.sql import Window

    window_spec = Window.partitionBy("code").orderBy(F.col(order_by).desc())

    return (df
            .withColumn("_row_num", F.row_number().over(window_spec))
            .filter(F.col("_row_num") == 1)
            .drop("_row_num"))


def compute_row_hash(df: DataFrame, columns: List[str], hash_col: str = "row_hash") -> DataFrame:
    """
    Compute MD5 hash of specified columns for change detection

    Args:
        df: Input DataFrame
        columns: List of columns to include in hash
        hash_col: Name for the hash column

    Returns:
        DataFrame with hash column added
    """
    # Create concatenated string with null-safe handling
    concat_expr = F.concat_ws(
        "||",
        *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in columns]
    )

    return df.withColumn(hash_col, F.md5(concat_expr))


def check_bounds(df: DataFrame, column: str, min_val: float, max_val: float) -> DataFrame:
    """
    Add a flag column indicating if values are out of bounds

    Args:
        df: Input DataFrame
        column: Column to check
        min_val: Minimum acceptable value
        max_val: Maximum acceptable value

    Returns:
        DataFrame with flag column added
    """
    flag_col = f"{column}_out_of_bounds"

    return df.withColumn(
        flag_col,
        F.when(
            (F.col(column).isNotNull()) &
            ((F.col(column) < min_val) | (F.col(column) > max_val)),
            True
        ).otherwise(False)
    )


def compute_completeness_score(df: DataFrame, weights: Dict[str, float]) -> DataFrame:
    """
    Compute weighted completeness score based on field presence

    Args:
        df: Input DataFrame
        weights: Dictionary mapping column names to weights (must sum to 1.0)

    Returns:
        DataFrame with completeness_score column
    """
    # Compute individual field scores
    score_expr = None

    for col_name, weight in weights.items():
        field_score = F.when(F.col(col_name).isNotNull(), F.lit(weight)).otherwise(F.lit(0.0))

        if score_expr is None:
            score_expr = field_score
        else:
            score_expr = score_expr + field_score

    return df.withColumn("completeness_score", F.round(score_expr, 2))


def collect_quality_issues(df: DataFrame, issue_columns: List[str]) -> DataFrame:
    """
    Collect quality issue flags into a JSON column

    Args:
        df: Input DataFrame with boolean flag columns
        issue_columns: List of flag column names

    Returns:
        DataFrame with quality_issues_json column
    """
    # Build JSON structure
    issues_struct = F.struct(*[
        F.col(col).alias(col.replace("_out_of_bounds", ""))
        for col in issue_columns
    ])

    return df.withColumn("quality_issues_json", F.to_json(issues_struct))


def save_run_metadata(metadata: Dict[str, Any]) -> None:
    """Save ETL run metadata to JSON file"""
    metadata["timestamp"] = datetime.now().isoformat()

    # Ensure directory exists
    Path(RUN_METADATA_PATH).parent.mkdir(parents=True, exist_ok=True)

    # Append to existing metadata file
    existing_runs = []
    if Path(RUN_METADATA_PATH).exists():
        with open(RUN_METADATA_PATH, 'r') as f:
            try:
                existing_runs = json.load(f)
            except json.JSONDecodeError:
                existing_runs = []

    existing_runs.append(metadata)

    with open(RUN_METADATA_PATH, 'w') as f:
        json.dump(existing_runs, f, indent=2)

    logger = setup_logger("Metadata")
    logger.info(f"Run metadata saved to {RUN_METADATA_PATH}")


def get_latest_run_metadata() -> Dict[str, Any]:
    """Get metadata from the most recent ETL run"""
    if not Path(RUN_METADATA_PATH).exists():
        return {}

    with open(RUN_METADATA_PATH, 'r') as f:
        runs = json.load(f)
        return runs[-1] if runs else {}
