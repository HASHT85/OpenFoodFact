"""
Unit and Integration Tests for OpenFoodFacts ETL Pipeline
M1 EISI/CDPIA/CYBER - Atelier Intégration des Données
"""
import pytest
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.utils import (
    normalize_tags,
    compute_salt_from_sodium,
    deduplicate_by_code,
    compute_row_hash,
    check_bounds,
    compute_completeness_score
)
from etl.schema_bronze import get_bronze_schema
from etl.settings import QUALITY_RULES


@pytest.fixture(scope="session")
def spark():
    """Create a Spark session for testing"""
    spark = (SparkSession.builder
             .appName("OFF_ETL_Tests")
             .master("local[2]")
             .config("spark.sql.session.timeZone", "UTC")
             .getOrCreate())

    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


@pytest.fixture
def sample_data(spark):
    """Create sample data for testing"""
    data = [
        {
            "code": "3017620422003",
            "product_name": "Nutella",
            "brands": "Ferrero",
            "categories_tags": ["en:breakfasts", "en:spreads"],
            "countries_tags": ["en:france", "en:italy"],
            "nutriscore_grade": "e",
            "nutriments": {
                "energy-kcal_100g": 539.0,
                "sugars_100g": 56.3,
                "fat_100g": 30.9,
                "salt_100g": 0.107,
                "sodium_100g": None
            },
            "last_modified_t": 1700000000
        },
        {
            "code": "1234567890123",
            "product_name": "Coca-Cola",
            "brands": "Coca Cola",
            "categories_tags": ["en:beverages"],
            "countries_tags": ["en:usa", "en:france"],
            "nutriscore_grade": "e",
            "nutriments": {
                "energy-kcal_100g": 42.0,
                "sugars_100g": 10.6,
                "fat_100g": 0.0,
                "salt_100g": None,
                "sodium_100g": 0.01
            },
            "last_modified_t": 1600000000
        }
    ]

    schema = get_bronze_schema()
    return spark.createDataFrame(data, schema=schema)


class TestUtils:
    """Test utility functions"""

    def test_normalize_tags(self, spark):
        """Test tag normalization removes language prefixes"""
        data = [
            (["en:breakfast", "fr:petit-dejeuner"],),
            (["en:beverages", "it:bevande"],)
        ]
        df = spark.createDataFrame(data, ["tags"])

        result = normalize_tags(df, "tags", "normalized_tags")
        normalized = result.select("normalized_tags").collect()

        assert "breakfast" in normalized[0]["normalized_tags"]
        assert "petit-dejeuner" in normalized[0]["normalized_tags"]
        assert "beverages" in normalized[1]["normalized_tags"]

    def test_compute_salt_from_sodium(self, spark):
        """Test salt computation from sodium"""
        data = [
            ("prod1", None, 1.0),  # salt missing, sodium present
            ("prod2", 2.5, 1.0),   # both present
            ("prod3", None, None)  # both missing
        ]
        df = spark.createDataFrame(data, ["code", "nutriments.salt_100g", "nutriments.sodium_100g"])

        result = compute_salt_from_sodium(df)
        rows = result.collect()

        # First product: salt = sodium * 2.5 = 2.5
        assert rows[0]["nutriments.salt_100g"] == pytest.approx(2.5)
        # Second product: existing salt preserved
        assert rows[1]["nutriments.salt_100g"] == 2.5
        # Third product: still None
        assert rows[2]["nutriments.salt_100g"] is None

    def test_deduplicate_by_code(self, spark):
        """Test deduplication keeps most recent record"""
        data = [
            ("12345", "Product A v1", 1000),
            ("12345", "Product A v2", 2000),  # Most recent
            ("67890", "Product B", 1500)
        ]
        df = spark.createDataFrame(data, ["code", "product_name", "last_modified_t"])

        result = deduplicate_by_code(df, "last_modified_t")

        assert result.count() == 2
        product_a = result.filter(F.col("code") == "12345").collect()[0]
        assert product_a["product_name"] == "Product A v2"

    def test_compute_row_hash(self, spark):
        """Test row hash computation for change detection"""
        data = [
            ("prod1", "Product 1", "Brand A"),
            ("prod2", "Product 2", "Brand B")
        ]
        df = spark.createDataFrame(data, ["code", "product_name", "brands"])

        result = compute_row_hash(df, ["product_name", "brands"], "hash")

        hashes = result.select("hash").collect()
        assert hashes[0]["hash"] is not None
        assert hashes[1]["hash"] is not None
        assert hashes[0]["hash"] != hashes[1]["hash"]

    def test_check_bounds(self, spark):
        """Test out-of-bounds detection"""
        data = [
            (50.0,),   # within bounds
            (150.0,),  # out of bounds
            (-10.0,),  # out of bounds
            (None,)    # null (should not flag)
        ]
        df = spark.createDataFrame(data, ["value"])

        result = check_bounds(df, "value", 0, 100)

        flags = result.select("value_out_of_bounds").collect()
        assert flags[0]["value_out_of_bounds"] == False
        assert flags[1]["value_out_of_bounds"] == True
        assert flags[2]["value_out_of_bounds"] == True
        assert flags[3]["value_out_of_bounds"] == False

    def test_compute_completeness_score(self, spark):
        """Test completeness score calculation"""
        data = [
            ("Product 1", "Brand A", "Category A"),  # All present
            ("Product 2", None, "Category B"),        # Missing brand
            (None, None, None)                         # All missing
        ]
        df = spark.createDataFrame(data, ["product_name", "brands", "category"])

        weights = {
            "product_name": 0.5,
            "brands": 0.3,
            "category": 0.2
        }

        result = compute_completeness_score(df, weights)
        scores = result.select("completeness_score").collect()

        assert scores[0]["completeness_score"] == 1.0  # All present
        assert scores[1]["completeness_score"] == 0.7  # Missing 0.3
        assert scores[2]["completeness_score"] == 0.0  # All missing


class TestQualityRules:
    """Test quality rules and validation"""

    def test_nutriment_bounds(self):
        """Test that quality rules are properly defined"""
        rules = QUALITY_RULES["nutriments"]

        assert "sugars_100g" in rules
        assert rules["sugars_100g"]["min"] == 0
        assert rules["sugars_100g"]["max"] == 100

        assert "salt_100g" in rules
        assert rules["salt_100g"]["max"] == 25

    def test_completeness_weights_sum_to_one(self):
        """Test that completeness weights sum to 1.0"""
        weights = QUALITY_RULES["completeness_weights"]
        total = sum(weights.values())

        assert total == pytest.approx(1.0, rel=1e-9)


class TestSchemas:
    """Test Spark schemas"""

    def test_bronze_schema_structure(self):
        """Test Bronze schema has required fields"""
        schema = get_bronze_schema()
        field_names = [field.name for field in schema.fields]

        required_fields = [
            "code",
            "product_name",
            "brands",
            "categories_tags",
            "nutriments",
            "nutriscore_grade",
            "last_modified_t"
        ]

        for field in required_fields:
            assert field in field_names, f"Missing required field: {field}"

    def test_bronze_schema_code_not_nullable(self):
        """Test that code field is not nullable"""
        schema = get_bronze_schema()
        code_field = next(f for f in schema.fields if f.name == "code")

        assert not code_field.nullable, "Code field should not be nullable"


class TestDataQuality:
    """Integration tests for data quality"""

    def test_sample_data_loading(self, spark, sample_data):
        """Test that sample data loads correctly"""
        assert sample_data.count() == 2

        # Check required fields
        assert sample_data.filter(F.col("code").isNull()).count() == 0

    def test_sample_data_completeness(self, spark, sample_data):
        """Test completeness scoring on sample data"""
        # Flatten nutriments first
        df = sample_data.select(
            "code",
            "product_name",
            "brands",
            "categories_tags",
            "nutriscore_grade",
            F.col("nutriments.energy-kcal_100g").alias("energy_kcal_100g"),
            F.col("nutriments.sugars_100g").alias("sugars_100g")
        )

        weights = {
            "product_name": 0.3,
            "brands": 0.3,
            "nutriscore_grade": 0.2,
            "energy_kcal_100g": 0.1,
            "sugars_100g": 0.1
        }

        result = compute_completeness_score(df, weights)

        # Both sample products should have high completeness
        scores = result.select("completeness_score").collect()
        assert all(score["completeness_score"] >= 0.8 for score in scores)

    def test_sample_data_bounds_checking(self, spark, sample_data):
        """Test bounds checking on sample data"""
        df = sample_data.select(
            "code",
            F.col("nutriments.sugars_100g").alias("sugars_100g"),
            F.col("nutriments.salt_100g").alias("salt_100g")
        )

        # Check sugars bounds
        result = check_bounds(df, "sugars_100g", 0, 100)

        # Nutella has 56.3g sugars (within bounds)
        # Coca-Cola has 10.6g sugars (within bounds)
        out_of_bounds = result.filter(F.col("sugars_100g_out_of_bounds")).count()
        assert out_of_bounds == 0


class TestEndToEnd:
    """End-to-end integration tests"""

    def test_sample_data_exists(self):
        """Test that sample data file exists"""
        sample_path = Path(__file__).parent / "sample_data.jsonl"
        assert sample_path.exists(), "Sample data file missing"

    def test_config_file_exists(self):
        """Test that configuration file exists"""
        config_path = Path(__file__).parent.parent / "conf" / "config.yaml"
        assert config_path.exists(), "Config file missing"


class TestPerformance:
    """Performance and scalability tests"""

    def test_large_dataset_deduplication(self, spark):
        """Test deduplication performance with larger dataset"""
        # Create 10000 records with some duplicates
        data = []
        for i in range(10000):
            code = str(i % 5000)  # 50% duplicates
            data.append((code, f"Product {code}", i))

        df = spark.createDataFrame(data, ["code", "product_name", "last_modified_t"])

        result = deduplicate_by_code(df, "last_modified_t")

        # Should have 5000 unique products
        assert result.count() == 5000


# Run tests with: pytest tests/test_etl.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
