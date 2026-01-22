import sys
import os
import subprocess
import logging

# Add current dir to path to import settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s MainOrchestrator: %(message)s')
logger = logging.getLogger("MainOrchestrator")

def run_step(script_name, args):
    """
    Runs a python script as a subprocess.
    """
    logger.info(f"-------- Starting Step: {script_name} --------")
    
    # We assume the scripts are in etl/jobs/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "jobs", script_name)
    
    cmd = [sys.executable, script_path] + args
    
    try:
        subprocess.check_call(cmd)
        logger.info(f"-------- Finished Step: {script_name} --------\n")
    except subprocess.CalledProcessError as e:
        logger.error(f"Step {script_name} failed with exit code {e.returncode}")
        # Continue or Exit? Exit is safer for ETL.
        sys.exit(e.returncode)

def main():
    # If input file is provided via CLI, use it. Otherwise, look for it in settings or default location.
    # For now, require it or a default test file.
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        # Default fallback for testing if exists
        default_test = os.path.join(settings.PROJECT_ROOT, "tests", "sample_data.jsonl")
        if os.path.exists(default_test):
            logger.info(f"No input file provided. Using default test file: {default_test}")
            input_file = default_test
        else:
            print("Usage: main.py <input_raw_file>")
            sys.exit(1)

    # 1. Bronze (Ingest)
    # Output: settings.BRONZE_DIR/<filename>.parquet
    # We'll pass the full output path
    bronze_out = os.path.join(settings.BRONZE_DIR, "products_raw.parquet")
    run_step("ingest.py", [input_file, bronze_out])
    
    # 2. Silver (Conform)
    # Input: bronze_out
    # Output: settings.SILVER_DIR/products_clean.parquet
    silver_out = os.path.join(settings.SILVER_DIR, "products_clean.parquet")
    run_step("conform.py", [bronze_out, silver_out])
    
    # 3. Gold (Load)
    # They take silver output as input
    # DB connection is handled via settings.py inside the scripts
    run_step("load_dimensions.py", [silver_out])
    run_step("load_product_scd.py", [silver_out])
    run_step("load_fact.py", [silver_out])

    logger.info("Pipeline Finished Successfully.")

if __name__ == "__main__":
    main()
