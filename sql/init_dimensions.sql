-- ==============================================================================
-- Initialize Dimension Tables with Reference Data
-- ==============================================================================

USE off_datamart;

-- ==============================================================================
-- 1. Populate dim_time (Pre-load date dimension)
-- ==============================================================================
-- This procedure generates date records for a given range
-- Note: In practice, this would be done by the ETL (load_dimensions.py)
-- but we provide this script for manual initialization if needed

-- Generate dates from 2020-01-01 to 2030-12-31
-- This is a placeholder - the actual population is done by Spark in load_dimensions.py

-- ==============================================================================
-- 2. Add Useful Indexes for Performance
-- ==============================================================================

-- Indexes on dim_product for common queries
CREATE INDEX IF NOT EXISTS idx_dim_product_code_current ON dim_product(code, is_current);
CREATE INDEX IF NOT EXISTS idx_dim_product_brand ON dim_product(brand_sk);
CREATE INDEX IF NOT EXISTS idx_dim_product_category ON dim_product(primary_category_sk);

-- Indexes on fact table for analytical queries
CREATE INDEX IF NOT EXISTS idx_fact_time ON fact_nutrition_snapshot(time_sk);
CREATE INDEX IF NOT EXISTS idx_fact_product_time ON fact_nutrition_snapshot(product_sk, time_sk);
CREATE INDEX IF NOT EXISTS idx_fact_nutriscore ON fact_nutrition_snapshot(nutriscore_grade);
CREATE INDEX IF NOT EXISTS idx_fact_completeness ON fact_nutrition_snapshot(completeness_score);

-- Index on dim_time for date range queries
CREATE INDEX IF NOT EXISTS idx_dim_time_date ON dim_time(date);
CREATE INDEX IF NOT EXISTS idx_dim_time_year_week ON dim_time(year, iso_week);

-- ==============================================================================
-- 3. Create Optional Bridge Table for Many-to-Many Product-Category
-- ==============================================================================
-- This table would store all categories for a product (not just primary)
-- Useful for more detailed category analysis

CREATE TABLE IF NOT EXISTS bridge_product_category (
    product_sk INT NOT NULL,
    category_sk INT NOT NULL,
    PRIMARY KEY (product_sk, category_sk),
    FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    FOREIGN KEY (category_sk) REFERENCES dim_category(category_sk)
) ENGINE=InnoDB;

-- ==============================================================================
-- 4. Create Optional dim_nutri (Separate Nutrition Scores Dimension)
-- ==============================================================================
-- If we want to dimension nutrition scores separately for better analysis

CREATE TABLE IF NOT EXISTS dim_nutri (
    nutri_sk INT AUTO_INCREMENT PRIMARY KEY,
    nutriscore_grade CHAR(1),
    nutriscore_score_min INT,
    nutriscore_score_max INT,
    nova_group INT,
    nova_description VARCHAR(255),
    ecoscore_grade CHAR(1),
    UNIQUE KEY uk_nutri_grades (nutriscore_grade, nova_group, ecoscore_grade)
) ENGINE=InnoDB;

-- Populate dim_nutri with common combinations (optional)
INSERT IGNORE INTO dim_nutri (nutriscore_grade, nutriscore_score_min, nutriscore_score_max, nova_group, nova_description, ecoscore_grade)
VALUES
    ('a', -15, -1, 1, 'Unprocessed or minimally processed', 'a'),
    ('b', 0, 2, 1, 'Unprocessed or minimally processed', 'b'),
    ('c', 3, 10, 2, 'Processed culinary ingredients', 'c'),
    ('d', 11, 18, 3, 'Processed foods', 'd'),
    ('e', 19, 100, 4, 'Ultra-processed foods', 'e');

-- ==============================================================================
-- 5. Create Audit Table for ETL Runs (Optional)
-- ==============================================================================
-- Track ETL execution history

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_name VARCHAR(100),
    status ENUM('started', 'success', 'failed'),
    records_processed INT,
    records_inserted INT,
    records_updated INT,
    duration_seconds INT,
    error_message TEXT,
    INDEX idx_run_timestamp (run_timestamp),
    INDEX idx_job_status (job_name, status)
) ENGINE=InnoDB;

-- ==============================================================================
-- 6. Create Aggregate Tables for Performance (Optional)
-- ==============================================================================
-- Pre-aggregate common queries for dashboard performance

CREATE TABLE IF NOT EXISTS agg_brand_monthly_stats (
    brand_sk INT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    total_products INT,
    avg_nutriscore_numeric DECIMAL(5,2),
    avg_completeness DECIMAL(5,3),
    products_grade_a INT,
    products_grade_b INT,
    products_grade_c INT,
    products_grade_d INT,
    products_grade_e INT,
    avg_sugars_100g DECIMAL(10,2),
    avg_salt_100g DECIMAL(10,3),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (brand_sk, year, month),
    FOREIGN KEY (brand_sk) REFERENCES dim_brand(brand_sk)
) ENGINE=InnoDB;

-- ==============================================================================
-- 7. Utility Views
-- ==============================================================================

-- View: Active Products with Full Details
CREATE OR REPLACE VIEW v_active_products AS
SELECT
    p.product_sk,
    p.code,
    p.product_name,
    b.brand_name,
    c.category_name_fr AS primary_category,
    p.countries_multi,
    p.effective_from,
    p.row_hash
FROM dim_product p
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
LEFT JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE p.is_current = 1;

-- View: Latest Nutrition Facts
CREATE OR REPLACE VIEW v_latest_nutrition_facts AS
SELECT
    p.code,
    p.product_name,
    b.brand_name,
    c.category_name_fr,
    f.energy_kcal_100g,
    f.sugars_100g,
    f.fat_100g,
    f.saturated_fat_100g,
    f.salt_100g,
    f.proteins_100g,
    f.fiber_100g,
    f.nutriscore_grade,
    f.nova_group,
    f.ecoscore_grade,
    f.completeness_score,
    t.date AS last_update_date
FROM (
    -- Get the most recent fact for each product
    SELECT
        product_sk,
        MAX(time_sk) AS latest_time_sk
    FROM fact_nutrition_snapshot
    GROUP BY product_sk
) latest
JOIN fact_nutrition_snapshot f
    ON latest.product_sk = f.product_sk
    AND latest.latest_time_sk = f.time_sk
JOIN dim_product p ON f.product_sk = p.product_sk
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
LEFT JOIN dim_category c ON p.primary_category_sk = c.category_sk
JOIN dim_time t ON f.time_sk = t.time_sk
WHERE p.is_current = 1;

-- ==============================================================================
-- 8. Data Quality Monitoring Views
-- ==============================================================================

-- View: Products with Quality Issues
CREATE OR REPLACE VIEW v_products_with_quality_issues AS
SELECT
    p.code,
    p.product_name,
    b.brand_name,
    f.completeness_score,
    f.quality_issues_json,
    CASE
        WHEN f.sugars_100g > 100 THEN 'High sugars'
        WHEN f.salt_100g > 25 THEN 'High salt'
        WHEN f.energy_kcal_100g > 900 THEN 'High energy'
        ELSE 'Other'
    END AS primary_issue
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE
    f.sugars_100g > 100
    OR f.salt_100g > 25
    OR f.energy_kcal_100g > 900
    OR f.completeness_score < 0.5;

-- View: Completeness Summary by Brand
CREATE OR REPLACE VIEW v_brand_completeness AS
SELECT
    b.brand_name,
    COUNT(DISTINCT p.product_sk) AS total_products,
    ROUND(AVG(f.completeness_score), 3) AS avg_completeness,
    SUM(CASE WHEN f.completeness_score >= 0.8 THEN 1 ELSE 0 END) AS high_quality_products,
    SUM(CASE WHEN f.completeness_score < 0.5 THEN 1 ELSE 0 END) AS low_quality_products,
    ROUND(
        SUM(CASE WHEN f.completeness_score >= 0.8 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        1
    ) AS pct_high_quality
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_brand b ON p.brand_sk = b.brand_sk
GROUP BY b.brand_name
HAVING COUNT(DISTINCT p.product_sk) >= 5
ORDER BY avg_completeness DESC;

-- ==============================================================================
-- Notes
-- ==============================================================================
-- 1. Run this script after schema.sql to initialize optional tables and indexes
-- 2. The dim_time population is actually done by Spark (etl/jobs/load_dimensions.py)
-- 3. Aggregate tables would need to be refreshed periodically (e.g., nightly job)
-- 4. Views provide convenient access patterns but may be slow on large datasets
-- ==============================================================================
