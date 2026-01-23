"""
Explicit Spark schemas for Bronze layer ingestion
Avoids schema inference which is not recommended for production
"""
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    IntegerType,
    DoubleType,
    ArrayType,
    MapType,
    BooleanType
)


def get_nutriments_schema() -> StructType:
    """Schema for nutriments nested structure"""
    return StructType([
        StructField("energy-kcal_100g", DoubleType(), True),
        StructField("energy-kj_100g", DoubleType(), True),
        StructField("sugars_100g", DoubleType(), True),
        StructField("fat_100g", DoubleType(), True),
        StructField("saturated-fat_100g", DoubleType(), True),
        StructField("salt_100g", DoubleType(), True),
        StructField("sodium_100g", DoubleType(), True),
        StructField("proteins_100g", DoubleType(), True),
        StructField("fiber_100g", DoubleType(), True),
        StructField("carbohydrates_100g", DoubleType(), True),
    ])


def get_bronze_schema() -> StructType:
    """
    Complete schema for OpenFoodFacts JSON/JSONL ingestion
    Focuses on fields needed for the Datamart
    """
    return StructType([
        # Identifiers
        StructField("code", StringType(), False),  # EAN-13 barcode (required)
        StructField("_id", StringType(), True),

        # Product Information
        StructField("product_name", StringType(), True),
        StructField("product_name_fr", StringType(), True),
        StructField("product_name_en", StringType(), True),
        StructField("generic_name", StringType(), True),
        StructField("brands", StringType(), True),
        StructField("brands_tags", ArrayType(StringType()), True),

        # Categories
        StructField("categories", StringType(), True),
        StructField("categories_tags", ArrayType(StringType()), True),

        # Countries
        StructField("countries", StringType(), True),
        StructField("countries_tags", ArrayType(StringType()), True),

        # Nutriments (nested structure)
        StructField("nutriments", get_nutriments_schema(), True),

        # Scores & Grades
        StructField("nutriscore_grade", StringType(), True),
        StructField("nutriscore_score", IntegerType(), True),
        StructField("nova_group", IntegerType(), True),
        StructField("ecoscore_grade", StringType(), True),
        StructField("ecoscore_score", IntegerType(), True),

        # Timestamps
        StructField("created_t", LongType(), True),
        StructField("last_modified_t", LongType(), True),
        StructField("last_modified_datetime", StringType(), True),

        # Additives & Allergens
        StructField("additives_tags", ArrayType(StringType()), True),
        StructField("allergens_tags", ArrayType(StringType()), True),

        # Other useful fields
        StructField("quantity", StringType(), True),
        StructField("serving_size", StringType(), True),
        StructField("packaging_tags", ArrayType(StringType()), True),
        StructField("labels_tags", ArrayType(StringType()), True),
        StructField("stores_tags", ArrayType(StringType()), True),

        # Completeness indicator (from OFF)
        StructField("completeness", DoubleType(), True),
    ])


def get_silver_schema() -> StructType:
    """
    Schema for Silver layer (cleaned and conformed data)
    This is the output of the conform job
    """
    return StructType([
        # Core identifiers
        StructField("code", StringType(), False),

        # Product info (with language resolution)
        StructField("product_name", StringType(), True),
        StructField("brands", StringType(), True),

        # Normalized arrays (without language prefixes)
        StructField("categories_normalized", ArrayType(StringType()), True),
        StructField("countries_normalized", ArrayType(StringType()), True),
        StructField("additives_normalized", ArrayType(StringType()), True),
        StructField("allergens_normalized", ArrayType(StringType()), True),

        # Primary category (first one)
        StructField("primary_category", StringType(), True),

        # Nutriments (flattened from nested structure)
        StructField("energy_kcal_100g", DoubleType(), True),
        StructField("energy_kj_100g", DoubleType(), True),
        StructField("sugars_100g", DoubleType(), True),
        StructField("fat_100g", DoubleType(), True),
        StructField("saturated_fat_100g", DoubleType(), True),
        StructField("salt_100g", DoubleType(), True),
        StructField("sodium_100g", DoubleType(), True),
        StructField("proteins_100g", DoubleType(), True),
        StructField("fiber_100g", DoubleType(), True),
        StructField("carbohydrates_100g", DoubleType(), True),

        # Scores
        StructField("nutriscore_grade", StringType(), True),
        StructField("nutriscore_score", IntegerType(), True),
        StructField("nova_group", IntegerType(), True),
        StructField("ecoscore_grade", StringType(), True),

        # Timestamps
        StructField("last_modified_t", LongType(), True),
        StructField("last_modified_datetime", StringType(), True),

        # Quality indicators
        StructField("completeness_score", DoubleType(), True),
        StructField("has_quality_issues", BooleanType(), True),

        # Quality issue flags
        StructField("energy_kcal_100g_out_of_bounds", BooleanType(), True),
        StructField("sugars_100g_out_of_bounds", BooleanType(), True),
        StructField("fat_100g_out_of_bounds", BooleanType(), True),
        StructField("saturated_fat_100g_out_of_bounds", BooleanType(), True),
        StructField("salt_100g_out_of_bounds", BooleanType(), True),
        StructField("sodium_100g_out_of_bounds", BooleanType(), True),
        StructField("proteins_100g_out_of_bounds", BooleanType(), True),
        StructField("fiber_100g_out_of_bounds", BooleanType(), True),

        # Computed hash for SCD2
        StructField("row_hash", StringType(), True),
    ])
