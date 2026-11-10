# Databricks notebook source
# MAGIC %md # FreshGroove — Batch Score via SQL
# MAGIC Creates waste_risk_scores table using rule-based SQL scoring
# MAGIC from gold_waste_risk_features (ML models are registered separately).

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Join supplier risk onto waste features, compute composite risk score
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.waste_risk_scores AS
# MAGIC SELECT
# MAGIC   f.date,
# MAGIC   f.store_id,
# MAGIC   f.sku_id,
# MAGIC   f.sku_name,
# MAGIC   f.category,
# MAGIC   f.region,
# MAGIC   f.supplier_id,
# MAGIC   f.on_hand_units,
# MAGIC   -- Composite waste risk score: blend 30d spoilage trend, supplier late rate, temp failure
# MAGIC   LEAST(1.0, GREATEST(0.0,
# MAGIC     COALESCE(f.spoilage_30d_avg, 0.10) * 0.5 +
# MAGIC     COALESCE(s.late_rate, 0.05) * 0.3 +
# MAGIC     CASE WHEN f.warehouse_temp_ok = 'false' THEN 0.15 ELSE 0.0 END +
# MAGIC     CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast'
# MAGIC               AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END
# MAGIC   )) AS waste_risk_score,
# MAGIC   -- Demand forecast: 7d average as proxy
# MAGIC   COALESCE(f.sales_7d_avg, f.units_sold, 0.0) AS demand_forecast_units,
# MAGIC   -- Supplier risk
# MAGIC   COALESCE(s.late_rate, 0.05) AS supplier_risk_score,
# MAGIC   -- Risk tier
# MAGIC   CASE
# MAGIC     WHEN LEAST(1.0, GREATEST(0.0,
# MAGIC       COALESCE(f.spoilage_30d_avg, 0.10) * 0.5 +
# MAGIC       COALESCE(s.late_rate, 0.05) * 0.3 +
# MAGIC       CASE WHEN f.warehouse_temp_ok = 'false' THEN 0.15 ELSE 0.0 END +
# MAGIC       CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast'
# MAGIC                 AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END
# MAGIC     )) >= 0.15 THEN 'HIGH'
# MAGIC     WHEN LEAST(1.0, GREATEST(0.0,
# MAGIC       COALESCE(f.spoilage_30d_avg, 0.10) * 0.5 +
# MAGIC       COALESCE(s.late_rate, 0.05) * 0.3 +
# MAGIC       CASE WHEN f.warehouse_temp_ok = 'false' THEN 0.15 ELSE 0.0 END +
# MAGIC       CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast'
# MAGIC                 AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END
# MAGIC     )) >= 0.08 THEN 'MEDIUM'
# MAGIC     ELSE 'LOW'
# MAGIC   END AS risk_tier,
# MAGIC   -- Recommended action
# MAGIC   CASE
# MAGIC     WHEN COALESCE(s.late_rate, 0.05) > 0.20 AND f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast'
# MAGIC       THEN CONCAT('Reduce order by ', CAST(CAST(f.on_hand_units * 0.25 AS INT) AS STRING), ' units. Consider backup supplier SUP-0007 for high-risk window.')
# MAGIC     WHEN COALESCE(f.spoilage_30d_avg, 0.0) > 0.12
# MAGIC       THEN CONCAT('Reduce order by ', CAST(CAST(f.on_hand_units * 0.20 AS INT) AS STRING), ' units. Spoilage trending above 12% — reduce stock depth.')
# MAGIC     WHEN COALESCE(s.late_rate, 0.0) > 0.18
# MAGIC       THEN 'Monitor supplier delivery. Late rate >18% — consider backup supplier for next window.'
# MAGIC     WHEN f.warehouse_temp_ok = 'false'
# MAGIC       THEN 'Check refrigeration. Temperature failure detected — inspect dairy/produce SKUs immediately.'
# MAGIC     ELSE 'No action needed. Continue standard replenishment.'
# MAGIC   END AS recommended_action,
# MAGIC   f.spoilage_pct,
# MAGIC   f.sales_7d_avg,
# MAGIC   f.spoilage_30d_avg
# MAGIC FROM matt_fe_bar_catalog.gold.gold_waste_risk_features f
# MAGIC LEFT JOIN matt_fe_bar_catalog.gold.gold_supplier_risk s ON f.supplier_id = s.supplier_id

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT
# MAGIC   risk_tier,
# MAGIC   COUNT(*) as count,
# MAGIC   ROUND(AVG(waste_risk_score), 3) as avg_score
# MAGIC FROM matt_fe_bar_catalog.gold.waste_risk_scores
# MAGIC GROUP BY risk_tier
# MAGIC ORDER BY count DESC

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Sample HIGH risk rows
# MAGIC SELECT store_id, sku_id, ROUND(waste_risk_score,3) as score,
# MAGIC        risk_tier, recommended_action
# MAGIC FROM matt_fe_bar_catalog.gold.waste_risk_scores
# MAGIC WHERE risk_tier = 'HIGH'
# MAGIC ORDER BY waste_risk_score DESC
# MAGIC LIMIT 10

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT COUNT(*) as total_rows,
# MAGIC        COUNT(CASE WHEN risk_tier='HIGH' THEN 1 END) as high_risk,
# MAGIC        COUNT(CASE WHEN risk_tier='MEDIUM' THEN 1 END) as medium_risk,
# MAGIC        COUNT(CASE WHEN risk_tier='LOW' THEN 1 END) as low_risk
# MAGIC FROM matt_fe_bar_catalog.gold.waste_risk_scores
