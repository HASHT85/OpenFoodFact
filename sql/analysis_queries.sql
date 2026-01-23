-- ==============================================================================
-- SQL Analytical Queries for OpenFoodFacts Datamart
-- M1 EISI/CDPIA/CYBER - Atelier Intégration des Données
-- ==============================================================================
-- These queries answer key business questions about nutrition and quality

USE off_datamart;

-- ==============================================================================
-- 1. Top 10 Marques par Proportion de Produits Nutri-Score A/B
-- ==============================================================================
-- Objectif : Identifier les marques avec la meilleure qualité nutritionnelle
-- Métrique : % de produits avec Nutri-Score A ou B

SELECT
    b.brand_name,
    COUNT(DISTINCT p.product_sk) AS total_products,
    SUM(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 ELSE 0 END) AS products_ab,
    ROUND(
        SUM(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT p.product_sk),
        2
    ) AS pct_nutriscore_ab
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_brand b ON p.brand_sk = b.brand_sk
GROUP BY b.brand_name
HAVING COUNT(DISTINCT p.product_sk) >= 5  -- Au moins 5 produits pour être significatif
ORDER BY pct_nutriscore_ab DESC, total_products DESC
LIMIT 10;


-- ==============================================================================
-- 2. Distribution Nutri-Score par Niveau 2 de Catégorie
-- ==============================================================================
-- Objectif : Comprendre la qualité nutritionnelle par catégorie de produits
-- Note : Simplifié car nous n'avons pas de hiérarchie complète dans cette version

SELECT
    c.category_name_fr,
    f.nutriscore_grade,
    COUNT(*) AS product_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY c.category_name_fr), 2) AS pct_in_category
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.nutriscore_grade IS NOT NULL
GROUP BY c.category_name_fr, f.nutriscore_grade
ORDER BY c.category_name_fr, f.nutriscore_grade;


-- ==============================================================================
-- 3. Heatmap Pays × Catégorie : Moyenne Sucres (sugars_100g)
-- ==============================================================================
-- Objectif : Identifier les combinaisons pays/catégorie avec le plus de sucre
-- Format : Table pivot pour visualisation heatmap

-- Version simple (liste)
SELECT
    c.category_name_fr,
    JSON_UNQUOTE(JSON_EXTRACT(p.countries_multi, '$[0]')) AS primary_country,
    COUNT(*) AS product_count,
    ROUND(AVG(f.sugars_100g), 2) AS avg_sugars_100g,
    ROUND(MIN(f.sugars_100g), 2) AS min_sugars_100g,
    ROUND(MAX(f.sugars_100g), 2) AS max_sugars_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.sugars_100g IS NOT NULL
  AND p.countries_multi IS NOT NULL
GROUP BY c.category_name_fr, primary_country
HAVING product_count >= 3  -- Au moins 3 produits pour être significatif
ORDER BY avg_sugars_100g DESC
LIMIT 50;


-- ==============================================================================
-- 4. Taux de Complétude des Nutriments par Marque
-- ==============================================================================
-- Objectif : Identifier les marques qui fournissent des données nutritionnelles complètes
-- Métrique : Score moyen de complétude et % de champs renseignés

SELECT
    b.brand_name,
    COUNT(DISTINCT p.product_sk) AS total_products,
    ROUND(AVG(f.completeness_score), 3) AS avg_completeness_score,
    -- Pourcentage de présence de chaque nutriment clé
    ROUND(SUM(CASE WHEN f.energy_kcal_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_energy,
    ROUND(SUM(CASE WHEN f.sugars_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_sugars,
    ROUND(SUM(CASE WHEN f.fat_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_fat,
    ROUND(SUM(CASE WHEN f.salt_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_salt,
    ROUND(SUM(CASE WHEN f.proteins_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_proteins,
    ROUND(SUM(CASE WHEN f.fiber_100g IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_fiber
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_brand b ON p.brand_sk = b.brand_sk
GROUP BY b.brand_name
HAVING COUNT(DISTINCT p.product_sk) >= 5
ORDER BY avg_completeness_score DESC, total_products DESC
LIMIT 20;


-- ==============================================================================
-- 5. Liste des Anomalies Détectées
-- ==============================================================================
-- Objectif : Auditer les produits avec des valeurs nutritionnelles aberrantes
-- Règles : sugars_100g > 100 OU salt_100g > 25

SELECT
    p.code,
    p.product_name,
    b.brand_name,
    f.sugars_100g,
    f.salt_100g,
    f.energy_kcal_100g,
    f.quality_issues_json,
    CASE
        WHEN f.sugars_100g > 100 THEN 'Sucres > 100g'
        WHEN f.salt_100g > 25 THEN 'Sel > 25g'
        WHEN f.energy_kcal_100g > 900 THEN 'Énergie > 900 kcal'
        ELSE 'Autre anomalie'
    END AS anomaly_type
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE
    f.sugars_100g > 100
    OR f.salt_100g > 25
    OR f.energy_kcal_100g > 900
    OR (f.energy_kcal_100g IS NOT NULL AND f.energy_kcal_100g < 0)
ORDER BY
    CASE
        WHEN f.sugars_100g > 100 THEN 1
        WHEN f.salt_100g > 25 THEN 2
        ELSE 3
    END,
    p.product_name;


-- ==============================================================================
-- 6. Évolution Hebdomadaire de la Complétude
-- ==============================================================================
-- Objectif : Suivre l'amélioration de la qualité des données dans le temps
-- Métrique : Score moyen de complétude par semaine

SELECT
    t.year,
    t.iso_week AS week_number,
    MIN(t.date) AS week_start_date,
    MAX(t.date) AS week_end_date,
    COUNT(DISTINCT f.product_sk) AS products_updated,
    ROUND(AVG(f.completeness_score), 3) AS avg_completeness_score,
    ROUND(AVG(CASE WHEN f.nutriscore_grade IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) AS pct_with_nutriscore,
    SUM(CASE WHEN f.completeness_score >= 0.8 THEN 1 ELSE 0 END) AS products_high_quality
FROM fact_nutrition_snapshot f
JOIN dim_time t ON f.time_sk = t.time_sk
GROUP BY t.year, t.iso_week
ORDER BY t.year DESC, t.iso_week DESC
LIMIT 52;  -- Dernière année


-- ==============================================================================
-- 7. Top Catégories avec le Plus d'Additifs en Moyenne
-- ==============================================================================
-- Note : Cette requête nécessiterait une table additifs ou un champ dans les faits
-- Pour cette version, on peut simuler avec NOVA group (niveau de transformation)

SELECT
    c.category_name_fr,
    COUNT(DISTINCT p.product_sk) AS total_products,
    ROUND(AVG(f.nova_group), 2) AS avg_nova_group,
    SUM(CASE WHEN f.nova_group >= 4 THEN 1 ELSE 0 END) AS ultra_processed_count,
    ROUND(SUM(CASE WHEN f.nova_group >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_ultra_processed
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.nova_group IS NOT NULL
GROUP BY c.category_name_fr
HAVING COUNT(DISTINCT p.product_sk) >= 10
ORDER BY avg_nova_group DESC, pct_ultra_processed DESC
LIMIT 20;


-- ==============================================================================
-- 8. Classement Marques par Qualité Nutritionnelle Moyenne
-- ==============================================================================
-- Objectif : Identifier les marques les plus saines
-- Métrique : Médiane des sucres, sel, et gras saturés

SELECT
    b.brand_name,
    COUNT(DISTINCT p.product_sk) AS total_products,
    -- Moyenne des nutriments (médiane serait préférable mais complexe en SQL)
    ROUND(AVG(f.sugars_100g), 2) AS avg_sugars_100g,
    ROUND(AVG(f.salt_100g), 2) AS avg_salt_100g,
    ROUND(AVG(f.saturated_fat_100g), 2) AS avg_saturated_fat_100g,
    -- Score composite (plus bas = meilleur)
    ROUND(
        COALESCE(AVG(f.sugars_100g), 0) * 0.4 +
        COALESCE(AVG(f.salt_100g), 0) * 40 +  -- Pondéré car en g (faible quantité)
        COALESCE(AVG(f.saturated_fat_100g), 0) * 0.6,
        2
    ) AS nutrition_score,
    -- Distribution Nutri-Score
    ROUND(SUM(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_ab
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE
    f.sugars_100g IS NOT NULL
    OR f.salt_100g IS NOT NULL
    OR f.saturated_fat_100g IS NOT NULL
GROUP BY b.brand_name
HAVING COUNT(DISTINCT p.product_sk) >= 10
ORDER BY nutrition_score ASC  -- Plus bas = meilleur
LIMIT 20;


-- ==============================================================================
-- 9. Analyse Croisée : Nutri-Score vs Complétude
-- ==============================================================================
-- Objectif : Vérifier si les produits avec meilleur score ont des données plus complètes

SELECT
    f.nutriscore_grade,
    COUNT(*) AS product_count,
    ROUND(AVG(f.completeness_score), 3) AS avg_completeness,
    ROUND(AVG(f.energy_kcal_100g), 1) AS avg_energy,
    ROUND(AVG(f.sugars_100g), 1) AS avg_sugars,
    ROUND(AVG(f.salt_100g), 2) AS avg_salt,
    ROUND(AVG(f.proteins_100g), 1) AS avg_proteins
FROM fact_nutrition_snapshot f
WHERE f.nutriscore_grade IS NOT NULL
GROUP BY f.nutriscore_grade
ORDER BY f.nutriscore_grade;


-- ==============================================================================
-- 10. Produits les Plus Récemment Modifiés avec Mauvaise Complétude
-- ==============================================================================
-- Objectif : Identifier les produits récents nécessitant une amélioration des données

SELECT
    p.code,
    p.product_name,
    b.brand_name,
    c.category_name_fr,
    t.date AS last_modified_date,
    f.completeness_score,
    -- Détail des champs manquants
    CASE WHEN f.nutriscore_grade IS NULL THEN '✗' ELSE '✓' END AS has_nutriscore,
    CASE WHEN f.energy_kcal_100g IS NULL THEN '✗' ELSE '✓' END AS has_energy,
    CASE WHEN f.sugars_100g IS NULL THEN '✗' ELSE '✓' END AS has_sugars,
    CASE WHEN f.salt_100g IS NULL THEN '✗' ELSE '✓' END AS has_salt,
    CASE WHEN f.proteins_100g IS NULL THEN '✗' ELSE '✓' END AS has_proteins,
    CASE WHEN f.fiber_100g IS NULL THEN '✗' ELSE '✓' END AS has_fiber
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk AND p.is_current = 1
JOIN dim_time t ON f.time_sk = t.time_sk
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
LEFT JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.completeness_score < 0.7
ORDER BY t.date DESC
LIMIT 50;


-- ==============================================================================
-- 11. Vue Matérialisée : Synthèse par Marque (Exemple)
-- ==============================================================================
-- Objectif : Créer une vue pré-calculée pour des dashboards
-- Note : MySQL ne supporte pas les vues matérialisées nativement,
-- mais on peut créer une table mise à jour périodiquement

CREATE OR REPLACE VIEW v_brand_summary AS
SELECT
    b.brand_sk,
    b.brand_name,
    COUNT(DISTINCT p.product_sk) AS total_products,
    ROUND(AVG(f.completeness_score), 3) AS avg_completeness,
    ROUND(AVG(f.sugars_100g), 2) AS avg_sugars,
    ROUND(AVG(f.salt_100g), 3) AS avg_salt,
    ROUND(AVG(f.energy_kcal_100g), 1) AS avg_energy,
    SUM(CASE WHEN f.nutriscore_grade = 'a' THEN 1 ELSE 0 END) AS count_grade_a,
    SUM(CASE WHEN f.nutriscore_grade = 'b' THEN 1 ELSE 0 END) AS count_grade_b,
    SUM(CASE WHEN f.nutriscore_grade = 'c' THEN 1 ELSE 0 END) AS count_grade_c,
    SUM(CASE WHEN f.nutriscore_grade = 'd' THEN 1 ELSE 0 END) AS count_grade_d,
    SUM(CASE WHEN f.nutriscore_grade = 'e' THEN 1 ELSE 0 END) AS count_grade_e,
    MAX(t.date) AS last_update_date
FROM dim_brand b
JOIN dim_product p ON b.brand_sk = p.brand_sk AND p.is_current = 1
JOIN fact_nutrition_snapshot f ON p.product_sk = f.product_sk
JOIN dim_time t ON f.time_sk = t.time_sk
GROUP BY b.brand_sk, b.brand_name;


-- ==============================================================================
-- 12. Requête de Validation : Intégrité Référentielle
-- ==============================================================================
-- Objectif : Vérifier qu'il n'y a pas d'orphelins dans les faits

SELECT
    'Fact records without valid product' AS check_name,
    COUNT(*) AS issue_count
FROM fact_nutrition_snapshot f
LEFT JOIN dim_product p ON f.product_sk = p.product_sk
WHERE p.product_sk IS NULL

UNION ALL

SELECT
    'Products without brand' AS check_name,
    COUNT(*) AS issue_count
FROM dim_product p
WHERE p.brand_sk IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dim_brand b WHERE b.brand_sk = p.brand_sk)

UNION ALL

SELECT
    'Products without category' AS check_name,
    COUNT(*) AS issue_count
FROM dim_product p
WHERE p.primary_category_sk IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dim_category c WHERE c.category_sk = p.primary_category_sk);


-- ==============================================================================
-- Notes d'Utilisation
-- ==============================================================================
-- 1. Exécutez ces requêtes après avoir chargé les données dans le datamart
-- 2. Certaines requêtes peuvent être lentes sur de gros volumes → ajouter des index
-- 3. Les résultats peuvent être exportés en CSV pour visualisation (Excel, Tableau, etc.)
-- 4. Pour des dashboards temps réel, considérez l'utilisation de vues ou tables agrégées
-- ==============================================================================
