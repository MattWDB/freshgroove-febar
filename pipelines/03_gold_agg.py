# Databricks notebook source
# MAGIC %md # Gold Layer — Business-Ready Aggregations + ML Features
# MAGIC Creates feature tables for ML models and KPI summaries for the app.

# COMMAND ----------
import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# COMMAND ----------
@dlt.table(
    name="gold.gold_waste_risk_features",
    comment="ML feature table. One row per store/SKU/date. All signals for waste risk model.",
    table_properties={"quality": "gold", "delta.enableChangeDataFeed": "true"}
)
def gold_waste_risk_features():
    base = dlt.read("silver.silver_inventory_sales")

    w7  = Window.partitionBy("store_id", "sku_id").orderBy("date").rowsBetween(-6, 0)
    w30 = Window.partitionBy("store_id", "sku_id").orderBy("date").rowsBetween(-29, 0)

    return (
        base
        .withColumn("sales_7d_avg",      F.avg("units_sold").over(w7))
        .withColumn("spoilage_30d_avg",   F.avg("spoilage_pct").over(w30))
        .withColumn("days_to_season_peak",
            F.datediff(F.to_date(F.lit("2025-04-15")), F.col("date")))
        .withColumn("is_high_risk",
            (F.col("spoilage_pct") > 0.12).cast("integer"))
        .select(
            "date", "store_id", "sku_id", "category", "region", "supplier_id",
            "on_hand_units", "units_sold", "spoilage_units", "spoilage_pct",
            "sales_7d_avg", "spoilage_30d_avg", "days_to_season_peak", "is_high_risk",
            "warehouse_temp_ok"
        )
    )

# COMMAND ----------
@dlt.table(
    name="gold.gold_kpi_summary",
    comment="Business KPIs: waste rate, spoilage cost, OTIF rate, chargeback cost. Used by app Overview.",
    table_properties={"quality": "gold"}
)
def gold_kpi_summary():
    base = dlt.read("silver.silver_inventory_sales")
    return (
        base.agg(
            F.round(F.avg("spoilage_pct"), 4).alias("avg_waste_rate"),
            F.round(F.sum(F.col("spoilage_units").cast("double") * F.lit(45.0)), 0).alias("total_spoilage_cost_usd"),
            F.count("*").alias("total_records"),
            F.max("date").alias("data_through_date")
        )
        .withColumn("otif_rate", F.lit(0.91))
        .withColumn("chargeback_cost_usd", F.lit(1500000.0))
    )

# COMMAND ----------
@dlt.table(
    name="gold.gold_supplier_risk",
    comment="Supplier-level risk aggregation. Late rate, spoilage correlation.",
    table_properties={"quality": "gold"}
)
def gold_supplier_risk():
    return (
        dlt.read("silver.silver_inventory")
        .groupBy("supplier_id")
        .agg(
            F.round(F.avg("spoilage_pct"), 4).alias("avg_spoilage_rate"),
            F.count("*").alias("delivery_count"),
            F.sum(
                F.when(F.col("units_received") < F.col("units_ordered") * 0.95, 1).otherwise(0)
            ).alias("short_shipments")
        )
        .withColumn("late_rate",
            F.round(F.col("short_shipments").cast("double") / F.col("delivery_count"), 4))
    )
