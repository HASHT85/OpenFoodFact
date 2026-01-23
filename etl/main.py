"""
Main ETL Pipeline Orchestrator
Executes the complete ETL flow: Bronze -> Silver -> Gold
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path

from etl.utils import create_spark_session, setup_logger, save_run_metadata
from etl.jobs.ingest import run_ingest_job
from etl.jobs.conform import run_conform_job
from etl.jobs.load_dimensions import run_load_dimensions_job
from etl.jobs.load_product_scd import run_load_product_scd_job
from etl.jobs.load_fact import run_load_fact_job
from etl.jobs.quality_report import run_quality_report_job


logger = setup_logger("MainETL")


def run_full_pipeline(input_path: str, skip_ingest: bool = False) -> dict:
    """
    Execute the complete ETL pipeline

    Args:
        input_path: Path to input JSONL/JSON file
        skip_ingest: If True, skip Bronze ingestion (use existing Bronze data)

    Returns:
        Dictionary with complete pipeline metrics
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("STARTING FULL ETL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Start time: {start_time}")
    logger.info(f"Input path: {input_path}")
    logger.info("=" * 80)

    spark = create_spark_session("OFF_ETL_Pipeline")
    pipeline_metrics = {
        "start_time": start_time.isoformat(),
        "input_path": input_path,
        "jobs": {}
    }

    try:
        # Step 1: Bronze Ingestion
        if not skip_ingest:
            logger.info("\n[1/6] Running Bronze Ingestion...")
            metrics_ingest = run_ingest_job(spark, input_path)
            pipeline_metrics["jobs"]["ingest"] = metrics_ingest
        else:
            logger.info("\n[1/6] Skipping Bronze Ingestion (using existing data)")

        # Step 2: Silver Conformation
        logger.info("\n[2/6] Running Silver Conformation...")
        metrics_conform = run_conform_job(spark)
        pipeline_metrics["jobs"]["conform"] = metrics_conform

        # Step 3: Load Dimensions
        logger.info("\n[3/6] Loading Dimensions...")
        metrics_dims = run_load_dimensions_job(spark)
        pipeline_metrics["jobs"]["load_dimensions"] = metrics_dims

        # Step 4: Load Product SCD2
        logger.info("\n[4/6] Loading Products (SCD2)...")
        metrics_product = run_load_product_scd_job(spark)
        pipeline_metrics["jobs"]["load_product_scd"] = metrics_product

        # Step 5: Load Fact Table
        logger.info("\n[5/6] Loading Fact Table...")
        metrics_fact = run_load_fact_job(spark)
        pipeline_metrics["jobs"]["load_fact"] = metrics_fact

        # Step 6: Quality Report
        logger.info("\n[6/6] Generating Quality Report...")
        metrics_quality = run_quality_report_job(spark)
        pipeline_metrics["jobs"]["quality_report"] = {
            "report_file": metrics_quality.get("report_file"),
            "total_records": metrics_quality.get("total_records"),
            "alerts": len(metrics_quality.get("alerts", []))
        }

        # Pipeline summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        pipeline_metrics["end_time"] = end_time.isoformat()
        pipeline_metrics["duration_seconds"] = duration
        pipeline_metrics["status"] = "success"

        logger.info("\n" + "=" * 80)
        logger.info("ETL PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 80)

        # Save run metadata
        save_run_metadata(pipeline_metrics)

        return pipeline_metrics

    except Exception as e:
        logger.error(f"\n{'=' * 80}")
        logger.error("ETL PIPELINE FAILED")
        logger.error(f"{'=' * 80}")
        logger.error(f"Error: {e}")
        logger.error(f"{'=' * 80}")

        pipeline_metrics["status"] = "failed"
        pipeline_metrics["error"] = str(e)
        pipeline_metrics["end_time"] = datetime.now().isoformat()

        save_run_metadata(pipeline_metrics)

        raise

    finally:
        spark.stop()


def print_pipeline_summary(metrics: dict) -> None:
    """
    Print a human-readable summary of the pipeline execution
    """
    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Status: {metrics['status'].upper()}")
    print(f"Duration: {metrics.get('duration_seconds', 0):.2f} seconds")
    print()

    if "jobs" in metrics:
        print("Job Results:")
        print("-" * 80)

        # Ingest
        if "ingest" in metrics["jobs"]:
            ingest = metrics["jobs"]["ingest"]
            print(f"  [Bronze] Ingestion:")
            print(f"    Records ingested: {ingest.get('total_records', 0)}")

        # Conform
        if "conform" in metrics["jobs"]:
            conform = metrics["jobs"]["conform"]
            print(f"  [Silver] Conformation:")
            print(f"    Records processed: {conform.get('total_records', 0)}")
            print(f"    Quality issues: {conform.get('records_with_quality_issues', 0)} ({conform.get('quality_issue_rate', 0)}%)")
            print(f"    Avg completeness: {conform.get('avg_completeness_score', 0)}")

        # Dimensions
        if "load_dimensions" in metrics["jobs"]:
            dims = metrics["jobs"]["load_dimensions"]
            print(f"  [Gold] Dimensions:")
            for dim in dims.get("dimensions_loaded", []):
                print(f"    {dim['dimension']}: {dim.get('inserted', 0)} inserted")

        # Product SCD2
        if "load_product_scd" in metrics["jobs"]:
            product = metrics["jobs"]["load_product_scd"]
            print(f"  [Gold] Products (SCD2):")
            print(f"    New: {product.get('new_products', 0)}")
            print(f"    Updated: {product.get('updated_products', 0)}")
            print(f"    Unchanged: {product.get('unchanged_products', 0)}")

        # Fact
        if "load_fact" in metrics["jobs"]:
            fact = metrics["jobs"]["load_fact"]
            print(f"  [Gold] Fact Table:")
            print(f"    Records loaded: {fact.get('total_records', 0)}")
            print(f"    With quality issues: {fact.get('records_with_quality_issues', 0)}")

        # Quality Report
        if "quality_report" in metrics["jobs"]:
            quality = metrics["jobs"]["quality_report"]
            print(f"  Quality Report:")
            print(f"    Report file: {quality.get('report_file', 'N/A')}")
            print(f"    Alerts: {quality.get('alerts', 0)}")

    print("=" * 80)


def main():
    """
    CLI entry point for the ETL pipeline
    """
    parser = argparse.ArgumentParser(
        description="OpenFoodFacts ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with input file
  python -m etl.main data/openfoodfacts-products.jsonl

  # Run with existing Bronze data (skip ingestion)
  python -m etl.main --skip-ingest

  # Run individual jobs
  python -m etl.jobs.ingest data/input.jsonl
  python -m etl.jobs.conform
  python -m etl.jobs.load_dimensions
  python -m etl.jobs.load_product_scd
  python -m etl.jobs.load_fact
  python -m etl.jobs.quality_report
        """
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        default=None,
        help="Path to input JSONL/JSON file (required unless --skip-ingest is used)"
    )

    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip Bronze ingestion and use existing Bronze data"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.skip_ingest and not args.input_path:
        parser.error("input_path is required unless --skip-ingest is used")

    if args.skip_ingest and not args.input_path:
        # Provide a dummy path when skipping ingest
        args.input_path = "N/A (skipped)"

    # Verify input file exists (if not skipping ingest)
    if not args.skip_ingest:
        input_file = Path(args.input_path)
        if not input_file.exists():
            logger.error(f"Input file not found: {args.input_path}")
            sys.exit(1)

    # Run pipeline
    try:
        metrics = run_full_pipeline(args.input_path, args.skip_ingest)
        print_pipeline_summary(metrics)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
