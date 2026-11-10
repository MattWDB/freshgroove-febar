# Databricks notebook source
# MAGIC %md # Create Operational Tables for FreshGroove App
# MAGIC Creates reorder_queue and kpi_live as Delta tables in gold schema.
# MAGIC These serve as the operational serving layer with write-back support.

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Operational reorder queue (HIGH + MEDIUM risk SKUs)
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.reorder_queue AS
# MAGIC SELECT
# MAGIC   CAST(monotonically_increasing_id() AS BIGINT) AS queue_id,
# MAGIC   date,
# MAGIC   store_id,
# MAGIC   sku_id,
# MAGIC   sku_name,
# MAGIC   category,
# MAGIC   region,
# MAGIC   supplier_id,
# MAGIC   CAST(waste_risk_score AS DOUBLE) AS waste_risk_score,
# MAGIC   risk_tier,
# MAGIC   recommended_action,
# MAGIC   CAST(on_hand_units AS INT) AS on_hand_units,
# MAGIC   'open' AS status,
# MAGIC   CAST(NULL AS STRING) AS acknowledged_by,
# MAGIC   CAST(NULL AS TIMESTAMP) AS acknowledged_at,
# MAGIC   current_timestamp() AS inserted_at
# MAGIC FROM matt_fe_bar_catalog.gold.waste_risk_scores
# MAGIC WHERE risk_tier IN ('HIGH', 'MEDIUM')
# MAGIC ORDER BY waste_risk_score DESC

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Enable Delta CDF for write-back audit trail
# MAGIC ALTER TABLE matt_fe_bar_catalog.gold.reorder_queue
# MAGIC SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT risk_tier, COUNT(*) as count
# MAGIC FROM matt_fe_bar_catalog.gold.reorder_queue
# MAGIC GROUP BY risk_tier
# MAGIC ORDER BY count DESC

# COMMAND ----------
# MAGIC %sql
# MAGIC -- KPI summary table for app Overview
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.kpi_live AS
# MAGIC SELECT
# MAGIC   'waste_rate' AS metric_name,
# MAGIC   CAST(avg_waste_rate AS DOUBLE) AS metric_value,
# MAGIC   'Waste Rate' AS metric_label
# MAGIC FROM matt_fe_bar_catalog.gold.gold_kpi_summary
# MAGIC UNION ALL
# MAGIC SELECT
# MAGIC   'spoilage_cost_usd',
# MAGIC   CAST(total_spoilage_cost_usd AS DOUBLE),
# MAGIC   'Spoilage Cost / Year (Est.)'
# MAGIC FROM matt_fe_bar_catalog.gold.gold_kpi_summary
# MAGIC UNION ALL
# MAGIC SELECT 'otif_rate', 0.91, 'OTIF Rate'
# MAGIC UNION ALL
# MAGIC SELECT 'chargeback_cost_usd', 1500000.0, 'Chargeback Cost / Year'

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT * FROM matt_fe_bar_catalog.gold.kpi_live

# COMMAND ----------
print("Operational tables created:")
reorder_count = spark.table("matt_fe_bar_catalog.gold.reorder_queue").count()
kpi_count = spark.table("matt_fe_bar_catalog.gold.kpi_live").count()
print(f"  reorder_queue: {reorder_count:,} rows")
print(f"  kpi_live: {kpi_count} rows")
