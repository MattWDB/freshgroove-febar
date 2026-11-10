# Databricks notebook source
# MAGIC %md # FreshGroove — GenAI Layer: AI Functions on PDFs and Disruptions
# MAGIC Uses Databricks AI Functions to extract structured data from supplier PDFs
# MAGIC and summarize weather disruption events.

# COMMAND ----------
# MAGIC %sql
# MAGIC -- AI FUNCTION 1: Parse supplier ASN PDFs
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.gold_asn_extracted AS
# MAGIC SELECT
# MAGIC   path,
# MAGIC   content,
# MAGIC   ai_extract(
# MAGIC     content,
# MAGIC     named_struct(
# MAGIC       'asn_number', 'The ASN number starting with ASN-',
# MAGIC       'supplier_id', 'The Supplier ID starting with SUP-',
# MAGIC       'promised_delivery_date', 'The Promised Delivery date in YYYY-MM-DD format',
# MAGIC       'carrier', 'The carrier company name',
# MAGIC       'is_at_risk', 'Whether the Risk Flag says YES (true) or NO (false)',
# MAGIC       'total_units', 'The Total Units as a number'
# MAGIC     )
# MAGIC   ) AS extracted
# MAGIC FROM read_files(
# MAGIC   '/Volumes/matt_fe_bar_catalog/bronze/raw_landing/supplier_asn_pdfs/',
# MAGIC   format => 'binaryFile'
# MAGIC )
# MAGIC WHERE path LIKE '%.pdf'
# MAGIC LIMIT 30

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT
# MAGIC   extracted:asn_number::string AS asn_number,
# MAGIC   extracted:supplier_id::string AS supplier_id,
# MAGIC   extracted:promised_delivery_date::string AS promised_date,
# MAGIC   extracted:carrier::string AS carrier,
# MAGIC   extracted:is_at_risk::string AS is_at_risk,
# MAGIC   extracted:total_units::int AS total_units
# MAGIC FROM matt_fe_bar_catalog.gold.gold_asn_extracted
# MAGIC WHERE extracted:is_at_risk::string = 'true'
# MAGIC LIMIT 10

# COMMAND ----------
# MAGIC %sql
# MAGIC -- AI FUNCTION 2: Summarize disruption events
# MAGIC CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.gold_disruption_signals AS
# MAGIC SELECT
# MAGIC   event_date, region, event_type, severity, description,
# MAGIC   ai_summarize(
# MAGIC     description,
# MAGIC     'Summarize in one sentence the supply chain impact of this event for a grocery company.'
# MAGIC   ) AS impact_summary,
# MAGIC   ai_classify(
# MAGIC     description,
# MAGIC     array('weather_delay', 'port_congestion', 'supplier_issue', 'demand_spike', 'other')
# MAGIC   ) AS classified_type
# MAGIC FROM matt_fe_bar_catalog.silver.silver_disruptions

# COMMAND ----------
# MAGIC %sql
# MAGIC SELECT event_date, region, event_type, impact_summary, classified_type
# MAGIC FROM matt_fe_bar_catalog.gold.gold_disruption_signals
# MAGIC ORDER BY event_date
# MAGIC LIMIT 10
