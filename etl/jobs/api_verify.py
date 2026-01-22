import sys
import os
import requests
import json
import logging

# Add parent dir for settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s APIVerifier: %(message)s')
logger = logging.getLogger("APIVerifier")

def verify_product_via_api(barcode):
    """
    Fetches product data from OpenFoodFacts API (v2) and prints key checks.
    """
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    logger.info(f"Fetching API for barcode: {barcode}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != 1:
            logger.warning("Product not found or status not OK in API.")
            return

        product = data.get("product", {})
        
        # Display Key Info
        logger.info(f"API Data for {barcode}:")
        logger.info(f"  - Name: {product.get('product_name')}")
        logger.info(f"  - Brands: {product.get('brands')}")
        logger.info(f"  - Nutri-Score: {product.get('nutriscore_grade')}")
        
        # Here we could implement comparison logic if we passed in our local data
        # For now, this serves as the "Ponctual Verification" tool
        
    except Exception as e:
        logger.error(f"API request failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: api_verify.py <barcode> [barcode2 ...]")
        # Default test if no arg
        verify_product_via_api("3017620422003") # Nutella France example
        # verify_product_via_api("737628064502") # Sample from test data
    else:
        for code in sys.argv[1:]:
            verify_product_via_api(code)
