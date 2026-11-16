-- Waste risk distribution by product category — HIGH vs MEDIUM vs LOW rows.
-- @param catalog STRING = matt_fe_bar_catalog
-- @param schema STRING = gold
SELECT
  category,
  risk_tier,
  CAST(COUNT(*) AS BIGINT) AS sku_count,
  CAST(ROUND(AVG(waste_risk_score) * 100, 1) AS DOUBLE) AS avg_risk_pct
FROM IDENTIFIER(:catalog || '.' || :schema || '.reorder_queue')
GROUP BY category, risk_tier
ORDER BY category, risk_tier
