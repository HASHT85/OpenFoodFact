import sys
import os
import json
from pyspark.sql import functions as F

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_spark_session, get_logger

def generate_quality_report(spark, silver_path, output_json_path):
    logger = get_logger("QualityReport")
    df = spark.read.parquet(silver_path)

    total_products = df.count()
    
    # Rule 1: Completeness of Nutri-Score
    with_score = df.filter(F.col("nutriscore_grade").isNotNull()).count()
    score_completeness = with_score / total_products if total_products > 0 else 0
    
    # Rule 2: Bound Checks (Sugars > 100)
    # Note: nutriments.sugars_100g might be string or float depending on casting in Silver.
    # We assumed Silver cast it.
    aberrant_sugars = df.filter(F.col("nutriments.sugars_100g") > 100).count()
    
    # Rule 3: Negative Values
    negative_energy = df.filter(F.col("nutriments.energy-kcal_100g") < 0).count()

    metrics = {
        "total_products_processed": total_products,
        "metrics": {
            "nutriscore_completeness_pct": round(score_completeness * 100, 2),
            "aberrant_sugars_count": aberrant_sugars,
            "negative_energy_count": negative_energy
        },
        "status": "SUCCESS"
    }

    # Write JSON
    with open(output_json_path, 'w') as f:
        json.dump(metrics, f, indent=4)
        
    logger.info(f"Quality report generated at {output_json_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: quality_report.py <silver_parquet_path> <output_json_report>")
        sys.exit(1)
        
    silver_path = sys.argv[1]
    output_path = sys.argv[2]
    
    spark = get_spark_session("OFF_Quality")
    generate_quality_report(spark, silver_path, output_path)
    spark.stop()
