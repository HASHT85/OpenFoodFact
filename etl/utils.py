from pyspark.sql import SparkSession
import logging

def get_spark_session(app_name="OFF_ETL"):
    """
    Creates or retrieves a Spark Session.
    Configured for local usage with appropriate memory settings for big data simulation if needed.
    """
    builder = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.session.timeZone", "UTC") \
        .config("spark.jars", "mysql-connector-j-8.0.33.jar") \
        .config("spark.driver.extraClassPath", "mysql-connector-j-8.0.33.jar")
        
    # In a real environment, we would start this differently
    # For this workshop, local[*] is fine
    return builder.getOrCreate()

def get_logger(name):
    """
    Returns a configured logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
