-- Top 20 highest waste-risk SKUs this week, ordered by risk score.
-- @param catalog STRING = matt_fe_bar_catalog
-- @param schema STRING = gold
SELECT
  store_id,
  sku_id,
  sku_name,
  region,
  CAST(ROUND(waste_risk_score * 100, 1) AS DOUBLE) AS risk_pct,
  risk_tier,
  CAST(on_hand_units AS BIGINT) AS on_hand_units
FROM IDENTIFIER(:catalog || '.' || :schema || '.reorder_queue')
WHERE risk_tier IN ('HIGH', 'MEDIUM')
ORDER BY waste_risk_score DESC
LIMIT 20
