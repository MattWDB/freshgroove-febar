# Databricks notebook source
# MAGIC %md # Bronze Layer — Raw Ingestion
# MAGIC Reads raw files from the Volume and creates Bronze Delta tables.
# MAGIC No transformations — preserve raw data exactly as-is.

# COMMAND ----------
import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import *

VOLUME_PATH = "/Volumes/matt_fe_bar_catalog/bronze/raw_landing"

# COMMAND ----------
@dlt.table(
    name="bronze.bronze_inventory_raw",
    comment="Raw store inventory records from ERP CSV feed. One row per store/SKU/date.",
    table_properties={"quality": "bronze"}
)
def bronze_inventory_raw():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{VOLUME_PATH}/store_inventory/")
    )

# COMMAND ----------
@dlt.table(
    name="bronze.bronze_sales_raw",
    comment="Raw POS sales transactions from TMS JSON feed.",
    table_properties={"quality": "bronze"}
)
def bronze_sales_raw():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"{VOLUME_PATH}/sales_transactions/")
    )

# COMMAND ----------
@dlt.table(
    name="bronze.bronze_disruptions_raw",
    comment="External disruption events (weather, port congestion, strikes).",
    table_properties={"quality": "bronze"}
)
def bronze_disruptions_raw():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(f"{VOLUME_PATH}/weather_disruptions/")
    )
