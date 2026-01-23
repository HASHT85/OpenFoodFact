"""
Quality Report Job
Generates comprehensive quality metrics and anomaly reports
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

from etl.utils import setup_logger
from etl.settings import SILVER_PATH, QUALITY_RULES, DATA_DIR


logger = setup_logger("QualityReport")


def compute_completeness_metrics(df: DataFrame) -> Dict[str, Any]:
    """
    Compute completeness metrics for key fields

    Returns:
        Dictionary with completeness statistics
    """
    logger.info("Computing completeness metrics...")

    total_records = df.count()

    # Fields to check
    fields = [
        "product_name",
        "brands",
        "primary_category",
        "nutriscore_grade",
        "energy_kcal_100g",
        "sugars_100g",
        "fat_100g",
        "saturated_fat_100g",
        "salt_100g",
        "proteins_100g",
        "fiber_100g"
    ]

    completeness_stats = {}

    for field in fields:
        non_null_count = df.filter(F.col(field).isNotNull()).count()
        completeness_pct = (non_null_count / total_records * 100) if total_records > 0 else 0
        completeness_stats[field] = {
            "non_null_count": non_null_count,
            "null_count": total_records - non_null_count,
            "completeness_pct": round(completeness_pct, 2)
        }

    # Average completeness score
    avg_completeness = df.agg(F.avg("completeness_score")).collect()[0][0]
    completeness_stats["overall_avg_score"] = round(float(avg_completeness), 3) if avg_completeness else 0

    return completeness_stats


def detect_anomalies(df: DataFrame) -> Dict[str, Any]:
    """
    Detect and count anomalies based on quality rules

    Returns:
        Dictionary with anomaly counts and examples
    """
    logger.info("Detecting anomalies...")

    anomalies = {}
    nutriment_rules = QUALITY_RULES["nutriments"]

    for column, bounds in nutriment_rules.items():
        # Count out of bounds values
        out_of_bounds_col = f"{column}_out_of_bounds"

        if out_of_bounds_col in df.columns:
            anomaly_count = df.filter(F.col(out_of_bounds_col) == True).count()

            if anomaly_count > 0:
                # Get some examples
                examples = (df
                           .filter(F.col(out_of_bounds_col) == True)
                           .select("code", "product_name", column)
                           .limit(5)
                           .collect())

                anomalies[column] = {
                    "count": anomaly_count,
                    "rule": f"{bounds['min']} <= {column} <= {bounds['max']}",
                    "examples": [
                        {
                            "code": row["code"],
                            "product_name": row["product_name"],
                            "value": float(row[column]) if row[column] is not None else None
                        }
                        for row in examples
                    ]
                }

    return anomalies


def compute_quality_distribution(df: DataFrame) -> Dict[str, Any]:
    """
    Compute distribution of quality scores and flags

    Returns:
        Dictionary with quality distribution stats
    """
    logger.info("Computing quality distribution...")

    total_records = df.count()

    # Completeness score distribution (buckets)
    completeness_buckets = (df
        .withColumn("score_bucket",
                   F.when(F.col("completeness_score") >= 0.8, "high (>=0.8)")
                   .when(F.col("completeness_score") >= 0.5, "medium (0.5-0.8)")
                   .otherwise("low (<0.5)"))
        .groupBy("score_bucket")
        .count()
        .collect())

    completeness_dist = {
        row["score_bucket"]: {
            "count": row["count"],
            "percentage": round(row["count"] / total_records * 100, 2)
        }
        for row in completeness_buckets
    }

    # Records with quality issues
    records_with_issues = df.filter(F.col("has_quality_issues") == True).count()
    issue_rate = (records_with_issues / total_records * 100) if total_records > 0 else 0

    return {
        "completeness_distribution": completeness_dist,
        "records_with_issues": records_with_issues,
        "issue_rate_pct": round(issue_rate, 2)
    }


def compute_nutriscore_distribution(df: DataFrame) -> Dict[str, Any]:
    """
    Compute Nutri-Score distribution

    Returns:
        Dictionary with Nutri-Score statistics
    """
    logger.info("Computing Nutri-Score distribution...")

    total_records = df.count()

    nutriscore_dist = (df
        .groupBy("nutriscore_grade")
        .count()
        .orderBy("nutriscore_grade")
        .collect())

    distribution = {}
    for row in nutriscore_dist:
        grade = row["nutriscore_grade"] if row["nutriscore_grade"] else "unknown"
        distribution[grade] = {
            "count": row["count"],
            "percentage": round(row["count"] / total_records * 100, 2)
        }

    return distribution


def generate_quality_report(spark: SparkSession) -> Dict[str, Any]:
    """
    Generate comprehensive quality report

    Returns:
        Dictionary with all quality metrics
    """
    logger.info("Generating quality report...")

    # Read Silver layer
    df_silver = spark.read.parquet(SILVER_PATH)
    total_records = df_silver.count()

    logger.info(f"Analyzing {total_records} records...")

    # Compute all metrics
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_records": total_records,
        "completeness_metrics": compute_completeness_metrics(df_silver),
        "anomalies": detect_anomalies(df_silver),
        "quality_distribution": compute_quality_distribution(df_silver),
        "nutriscore_distribution": compute_nutriscore_distribution(df_silver)
    }

    # Check against alert thresholds
    alerts = []
    avg_completeness = report["completeness_metrics"]["overall_avg_score"]
    threshold = QUALITY_RULES["alerts"]["completeness_threshold"]

    if avg_completeness < threshold:
        alerts.append({
            "type": "low_completeness",
            "message": f"Average completeness score ({avg_completeness}) is below threshold ({threshold})",
            "severity": "warning"
        })

    # Check anomaly counts
    total_anomalies = sum(anom["count"] for anom in report["anomalies"].values())
    anomaly_threshold = QUALITY_RULES["alerts"]["anomaly_threshold"]

    if total_anomalies > anomaly_threshold:
        alerts.append({
            "type": "high_anomalies",
            "message": f"Total anomalies ({total_anomalies}) exceeds threshold ({anomaly_threshold})",
            "severity": "warning"
        })

    report["alerts"] = alerts

    return report


def save_quality_report(report: Dict[str, Any], output_dir: Path = None) -> str:
    """
    Save quality report to JSON file

    Returns:
        Path to saved report file
    """
    if output_dir is None:
        output_dir = Path(DATA_DIR) / "quality_reports"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"quality_report_{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Quality report saved to: {filepath}")
    return str(filepath)


def print_report_summary(report: Dict[str, Any]) -> None:
    """
    Print a human-readable summary of the quality report
    """
    print("\n" + "=" * 80)
    print("QUALITY REPORT SUMMARY")
    print("=" * 80)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total Records: {report['total_records']}")
    print()

    print("COMPLETENESS METRICS:")
    print("-" * 80)
    comp_metrics = report['completeness_metrics']
    print(f"Overall Avg Score: {comp_metrics['overall_avg_score']}")
    print()
    print("Field-level completeness:")
    for field, stats in comp_metrics.items():
        if field != "overall_avg_score":
            print(f"  {field:30s}: {stats['completeness_pct']:6.2f}% ({stats['non_null_count']} records)")
    print()

    print("ANOMALIES DETECTED:")
    print("-" * 80)
    if report['anomalies']:
        for field, anomaly_info in report['anomalies'].items():
            print(f"  {field}: {anomaly_info['count']} anomalies")
            print(f"    Rule: {anomaly_info['rule']}")
    else:
        print("  No anomalies detected")
    print()

    print("QUALITY DISTRIBUTION:")
    print("-" * 80)
    qual_dist = report['quality_distribution']
    print(f"Records with quality issues: {qual_dist['records_with_issues']} ({qual_dist['issue_rate_pct']}%)")
    print()
    print("Completeness distribution:")
    for bucket, stats in qual_dist['completeness_distribution'].items():
        print(f"  {bucket:20s}: {stats['count']:6d} ({stats['percentage']:5.2f}%)")
    print()

    print("NUTRI-SCORE DISTRIBUTION:")
    print("-" * 80)
    for grade, stats in report['nutriscore_distribution'].items():
        print(f"  Grade {grade:8s}: {stats['count']:6d} ({stats['percentage']:5.2f}%)")
    print()

    if report['alerts']:
        print("ALERTS:")
        print("-" * 80)
        for alert in report['alerts']:
            print(f"  [{alert['severity'].upper()}] {alert['message']}")
        print()

    print("=" * 80)


def run_quality_report_job(spark: SparkSession) -> Dict[str, Any]:
    """
    Main entry point for quality report job

    Returns:
        Quality report dictionary
    """
    logger.info("=" * 80)
    logger.info("QUALITY REPORT JOB")
    logger.info("=" * 80)

    # Generate report
    report = generate_quality_report(spark)

    # Save to file
    report_path = save_quality_report(report)
    report["report_file"] = report_path

    # Print summary
    print_report_summary(report)

    logger.info("Quality report job complete")
    return report


if __name__ == "__main__":
    from etl.utils import create_spark_session

    spark = create_spark_session("OFF_Quality_Report")

    try:
        report = run_quality_report_job(spark)
        print("\n✓ Quality report generated successfully")
        print(f"Report saved to: {report['report_file']}")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()
