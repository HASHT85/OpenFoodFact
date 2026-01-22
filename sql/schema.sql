-- ==============================================================================
-- Schema DDL for OpenFoodFacts Datamart
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS off_datamart;
USE off_datamart;

-- ------------------------------------------------------------------------------
-- 1. Dimensions
-- ------------------------------------------------------------------------------

-- Dim Brand
CREATE TABLE IF NOT EXISTS dim_brand (
    brand_sk INT AUTO_INCREMENT PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- Dim Category
CREATE TABLE IF NOT EXISTS dim_category (
    category_sk INT AUTO_INCREMENT PRIMARY KEY,
    category_code VARCHAR(255) NOT NULL UNIQUE,
    category_name_fr VARCHAR(255),
    level INT,
    parent_category_sk INT
) ENGINE=InnoDB;

-- Dim Country
CREATE TABLE IF NOT EXISTS dim_country (
    country_sk INT AUTO_INCREMENT PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL UNIQUE,
    country_name_fr VARCHAR(255)
) ENGINE=InnoDB;

-- Dim Time
-- Typically pre-loaded or generated. Here we create structure.
CREATE TABLE IF NOT EXISTS dim_time (
    time_sk INT PRIMARY KEY, -- YYYYMMDD
    date DATE,
    year INT,
    month INT,
    day INT,
    week INT,
    iso_week INT
) ENGINE=InnoDB;

-- Dim Product (SCD Type 2)
CREATE TABLE IF NOT EXISTS dim_product (
    product_sk INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    product_name TEXT,
    brand_sk INT,
    primary_category_sk INT,
    countries_multi JSON, -- Stores array of country codes or names
    
    -- SCD Meta
    is_current BOOLEAN DEFAULT 1,
    effective_from TIMESTAMP,
    effective_to TIMESTAMP NULL,
    row_hash VARCHAR(32), -- MD5 for change detection

    INDEX idx_code_current (code, is_current),
    FOREIGN KEY (brand_sk) REFERENCES dim_brand(brand_sk),
    FOREIGN KEY (primary_category_sk) REFERENCES dim_category(category_sk)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. Facts
-- ------------------------------------------------------------------------------

-- Fact Nutrition Snapshot
CREATE TABLE IF NOT EXISTS fact_nutrition_snapshot (
    fact_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_sk INT NOT NULL,
    time_sk INT NOT NULL,
    
    -- Measures (100g)
    energy_kcal_100g DECIMAL(10, 2),
    fat_100g DECIMAL(10, 2),
    saturated_fat_100g DECIMAL(10, 2),
    sugars_100g DECIMAL(10, 2),
    salt_100g DECIMAL(10, 2),
    proteins_100g DECIMAL(10, 2),
    fiber_100g DECIMAL(10, 2),
    sodium_100g DECIMAL(10, 2),
    
    -- Scores & Attributes
    nutriscore_grade CHAR(1),
    nova_group INT,
    ecoscore_grade CHAR(1),
    
    -- Quality Metrics
    completeness_score DECIMAL(3, 2), -- 0.00 to 1.00
    quality_issues_json JSON,
    
    FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    -- FOREIGN KEY (time_sk) REFERENCES dim_time(time_sk), -- Optional enforcement
    
    INDEX idx_product_time (product_sk, time_sk)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. Utility / Staging Tables
-- ------------------------------------------------------------------------------
-- Used by Spark for intermediate operations if needed (e.g. tmp_expire_products)
-- Spark usually creates these on the fly, but good to know.
