from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType, ArrayType, MapType

def get_bronze_schema():
    """
    Returns the Spark StructType for the OpenFoodFacts Dataset.
    Focuses on the fields required for the workshop.
    """
    # Note: nutriments can be messy, but usually it's a struct. 
    # Provided JSON sample suggests simple fields inside nutriments.
    nutriments_schema = StructType([
        StructField("energy-kcal_100g", DoubleType(), True),
        StructField("energy_100g", DoubleType(), True),
        StructField("fat_100g", DoubleType(), True),
        StructField("saturated-fat_100g", DoubleType(), True),
        StructField("carbohydrates_100g", DoubleType(), True),
        StructField("sugars_100g", DoubleType(), True),
        StructField("fiber_100g", DoubleType(), True),
        StructField("proteins_100g", DoubleType(), True),
        StructField("salt_100g", DoubleType(), True),
        StructField("sodium_100g", DoubleType(), True)
    ])

    schema = StructType([
        StructField("code", StringType(), True),
        StructField("product_name", StringType(), True),
        StructField("product_name_fr", StringType(), True),
        StructField("brands", StringType(), True),
        StructField("categories_tags", ArrayType(StringType()), True),
        StructField("countries_tags", ArrayType(StringType()), True),
        StructField("nutriscore_grade", StringType(), True),
        StructField("nova_group", LongType(), True),
        StructField("ecoscore_grade", StringType(), True),
        StructField("nutriments", nutriments_schema, True),
        StructField("last_modified_t", LongType(), True),
        StructField("created_t", LongType(), True)
    ])
    return schema
