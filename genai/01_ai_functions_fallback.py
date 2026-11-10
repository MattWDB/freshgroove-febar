# Databricks notebook source
# MAGIC %md # GenAI Fallback — Structured extraction via regexp (no ai_extract needed)
# MAGIC Used when ai_extract/ai_summarize are not available in this workspace.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.gold_asn_extracted AS
# MAGIC SELECT
# MAGIC   path,
# MAGIC   content,
# MAGIC   regexp_extract(content, 'ASN Number:\\s+(ASN-\\d+)', 1) AS asn_number,
# MAGIC   regexp_extract(content, 'Supplier ID:\\s+(SUP-\\d+)', 1) AS supplier_id,
# MAGIC   regexp_extract(content, 'Promised Delivery:\\s+([0-9]{4}-[0-9]{2}-[0-9]{2})', 1) AS promised_date,
# MAGIC   regexp_extract(content, 'Carrier:\\s+([^\\n]+)', 1) AS carrier,
# MAGIC   CASE WHEN content LIKE '%YES - LATE DELIVERY%' THEN true ELSE false END AS is_at_risk,
# MAGIC   CAST(regexp_extract(content, 'Total Units: (\\d+)', 1) AS INT) AS total_units
# MAGIC FROM read_files(
# MAGIC   '/Volumes/matt_fe_bar_catalog/bronze/raw_landing/supplier_asn_pdfs/',
# MAGIC   format => 'binaryFile'
# MAGIC )
# MAGIC WHERE path LIKE '%.pdf'

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT asn_number, supplier_id, promised_date, carrier, is_at_risk, total_units
# MAGIC FROM matt_fe_bar_catalog.gold.gold_asn_extracted
# MAGIC WHERE is_at_risk = true
# MAGIC LIMIT 10

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT COUNT(*) as total, SUM(CASE WHEN is_at_risk THEN 1 ELSE 0 END) as at_risk_count
# MAGIC FROM matt_fe_bar_catalog.gold.gold_asn_extracted

# COMMAND ----------
# MAGIC %sql
# MAGIC -- Disruption signals with structured classification (no LLM needed)
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.gold_disruption_signals AS
# MAGIC SELECT
# MAGIC   event_date, region, event_type, severity, description,
# MAGIC   CONCAT('Supply chain impact: ', description) AS impact_summary,
# MAGIC   event_type AS classified_type
# MAGIC FROM matt_fe_bar_catalog.silver.silver_disruptions

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT event_date, region, event_type, severity, impact_summary
# MAGIC FROM matt_fe_bar_catalog.gold.gold_disruption_signals
# MAGIC ORDER BY event_date
# MAGIC LIMIT 10
