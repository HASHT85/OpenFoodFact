-- ==============================================================================
-- Requêtes Analytiques / Analytical Queries
-- ==============================================================================

-- 1. Top 10 marques par proportion de produits Nutri-Score A/B
-- (Combien de produits A/B sur le total de produits notés de la marque)
WITH BrandGraded AS (
    SELECT 
        d.brand_name,
        COUNT(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 END) as count_ab,
        COUNT(*) as total_graded
    FROM fact_nutrition_snapshot f
    JOIN dim_brand d ON f.brand_sk = d.brand_sk -- via product denorm or join
                 -- Note: fact tables usually link to product, then product links to brand.
                 JOIN dim_product p ON f.product_sk = p.product_sk
    WHERE f.nutriscore_grade IS NOT NULL
    GROUP BY d.brand_name
    HAVING total_graded > 10 -- Filtre pour éviter marques avec 1 seul produit
)
SELECT 
    brand_name,
    count_ab,
    total_graded,
    (count_ab / total_graded) * 100 as proportion_ab_pct
FROM BrandGraded
ORDER BY proportion_ab_pct DESC
LIMIT 10;

-- 2. Distribution Nutri-Score par niveau 2 de catégorie
-- Note: Requires dim_category to have hierarchy info. 
-- Assuming category_name_fr contains the level logic or we filter by level column.
SELECT 
    c.category_name_fr,
    f.nutriscore_grade,
    COUNT(*) as product_count
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE c.level = 2 -- Si niveau hiérarchique dispo
GROUP BY c.category_name_fr, f.nutriscore_grade
ORDER BY c.category_name_fr, f.nutriscore_grade;

-- 3. Heatmap (table) pays × catégorie : moyenne sugars_100g
SELECT 
    l.country_name_fr,
    c.category_name_fr,
    AVG(f.sugars_100g) as avg_sugar
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
-- Note: Product has Multi-Countries (JSON). 
-- This query is complex if we want to explode the JSON.
-- Assuming we use the "primary market" or joining with a bridge table if created.
-- If we joined via a bridge_product_country (not in schema yet, but implied by requirement).
-- Here we approximate by using the first country from the JSON or similar, or assuming a 'main_country' column.
-- Alternatively, if we loaded "dim_country" and linked it:
    JOIN dim_country l ON l.country_code = JSON_UNQUOTE(JSON_EXTRACT(p.countries_multi, '$[0]')) -- Taking first country
    JOIN dim_category c ON p.primary_category_sk = c.category_sk
GROUP BY l.country_name_fr, c.category_name_fr
LIMIT 100;

-- 4. Évolution hebdo de la complétude (via dim_time)
SELECT 
    t.year,
    t.week,
    AVG(f.completeness_score) as avg_completeness
FROM fact_nutrition_snapshot f
JOIN dim_time t ON f.time_sk = t.time_sk
GROUP BY t.year, t.week
ORDER BY t.year, t.week;

-- 5. Liste anomalies (ex. salt_100g > 25 ou sugars_100g > 80)
SELECT 
    p.code,
    p.product_name,
    f.salt_100g,
    f.sugars_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
WHERE f.salt_100g > 25 OR f.sugars_100g > 80
LIMIT 500;
