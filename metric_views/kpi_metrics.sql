-- FreshGroove Metric Views — used by Genie Agent
-- NOTE: Synthetic data ends 2026-03-31. Use MAX(date)-based windows, not CURRENT_DATE().

USE CATALOG matt_fe_bar_catalog;
USE SCHEMA gold;

-- Already created in Session 5. Documented here for reference.

-- v_waste_kpis: headline KPIs (last 30 days of synthetic data)
-- v_high_risk_skus: HIGH risk items sorted by risk score
-- v_supplier_risk_summary: supplier reliability ranking

-- Additional sample queries for Genie:

-- Which SKUs are at highest risk?
SELECT sku_id, sku_name, store_id, waste_risk_score, recommended_action
FROM matt_fe_bar_catalog.gold.waste_risk_scores
WHERE risk_tier = 'HIGH'
ORDER BY waste_risk_score DESC
LIMIT 10;

-- Current waste rate
SELECT waste_rate_pct FROM matt_fe_bar_catalog.gold.v_waste_kpis;

-- Which suppliers are causing the most risk?
SELECT supplier_id, late_rate_pct, avg_spoilage_pct
FROM matt_fe_bar_catalog.gold.v_supplier_risk_summary
WHERE risk_tier = 'HIGH'
ORDER BY late_rate_pct DESC;

-- How much would we save if we cut waste in half?
SELECT ROUND(total_spoilage_cost_usd / 2, 0) AS potential_savings
FROM matt_fe_bar_catalog.gold.v_waste_kpis;

-- Waste rate by region
SELECT region,
       ROUND(AVG(spoilage_pct) * 100, 1) AS waste_rate_pct,
       COUNT(DISTINCT store_id) AS stores
FROM matt_fe_bar_catalog.gold.gold_waste_risk_features
GROUP BY region
ORDER BY waste_rate_pct DESC;
