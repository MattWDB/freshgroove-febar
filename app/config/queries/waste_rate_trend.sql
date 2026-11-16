-- Monthly waste rate trend over time. Shows the April strawberry spike.
-- @param catalog STRING = matt_fe_bar_catalog
-- @param schema STRING = gold
SELECT
  DATE_TRUNC('month', date) AS month,
  CAST(ROUND(AVG(spoilage_pct) * 100, 2) AS DOUBLE) AS waste_rate_pct
FROM IDENTIFIER(:catalog || '.' || :schema || '.gold_waste_risk_features')
GROUP BY 1
ORDER BY 1
