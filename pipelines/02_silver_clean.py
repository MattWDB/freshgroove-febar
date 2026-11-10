# Databricks notebook source
# MAGIC %md # Silver Layer — Clean, Join, Data Quality
# MAGIC Cleans raw data, enforces DQ expectations, joins inventory + sales.

# COMMAND ----------
import dlt
from pyspark.sql import functions as F

# COMMAND ----------
@dlt.table(
    name="silver.silver_inventory",
    comment="Cleaned inventory records. Null spoilage filled with 0. DQ rules enforced.",
    table_properties={"quality": "silver"}
)
@dlt.expect_or_drop("valid_spoilage_units", "spoilage_units >= 0 AND spoilage_units <= on_hand_units")
@dlt.expect_or_drop("valid_date", "date IS NOT NULL")
@dlt.expect("store_exists", "store_id IS NOT NULL")
@dlt.expect("sku_exists", "sku_id IS NOT NULL")
def silver_inventory():
    return (
        dlt.read_stream("bronze.bronze_inventory_raw")
        .withColumn("spoilage_pct",
            F.when(F.col("on_hand_units") > 0,
                   F.col("spoilage_units").cast("double") / F.col("on_hand_units").cast("double"))
            .otherwise(0.0))
        .withColumn("date", F.to_date("date"))
        .withColumn("week", F.date_trunc("week", F.to_date("date")))
        .withColumn("month", F.date_trunc("month", F.to_date("date")))
        .withColumn("on_hand_units", F.col("on_hand_units").cast("integer"))
        .withColumn("units_ordered", F.col("units_ordered").cast("integer"))
        .withColumn("units_received", F.col("units_received").cast("integer"))
        .withColumn("spoilage_units", F.col("spoilage_units").cast("integer"))
        .dropDuplicates(["date", "store_id", "sku_id"])
    )

# COMMAND ----------
@dlt.table(
    name="silver.silver_sales",
    comment="Cleaned sales transactions. Negative units_sold set to 0.",
    table_properties={"quality": "silver"}
)
@dlt.expect_or_drop("valid_units", "units_sold >= 0")
@dlt.expect_or_drop("valid_date_sales", "date IS NOT NULL")
def silver_sales():
    return (
        dlt.read_stream("bronze.bronze_sales_raw")
        .withColumn("units_sold", F.greatest(F.col("units_sold").cast("integer"), F.lit(0)))
        .withColumn("unit_price", F.col("unit_price").cast("double"))
        .withColumn("date", F.to_date("date"))
        .withColumn("revenue", F.col("units_sold").cast("integer") * F.col("unit_price").cast("double"))
    )

# COMMAND ----------
@dlt.table(
    name="silver.silver_inventory_sales",
    comment="Inventory joined with sales. Core fact table for ML features and KPIs.",
    table_properties={"quality": "silver"}
)
def silver_inventory_sales():
    inv = dlt.read("silver.silver_inventory")
    sales = dlt.read("silver.silver_sales")
    return (
        inv.join(
            sales.select("date", "store_id", "sku_id", "units_sold", "revenue"),
            on=["date", "store_id", "sku_id"],
            how="left"
        )
        .withColumn("units_sold", F.coalesce(F.col("units_sold"), F.lit(0)))
        .withColumn("revenue", F.coalesce(F.col("revenue"), F.lit(0.0)))
    )

# COMMAND ----------
@dlt.table(
    name="silver.silver_disruptions",
    comment="Cleaned disruption events with severity scoring.",
    table_properties={"quality": "silver"}
)
def silver_disruptions():
    return (
        dlt.read_stream("bronze.bronze_disruptions_raw")
        .withColumn("event_date", F.to_date("event_date"))
        .withColumn("severity_score",
            F.when(F.col("severity") == "high", 3)
             .when(F.col("severity") == "medium", 2)
             .otherwise(1))
    )
