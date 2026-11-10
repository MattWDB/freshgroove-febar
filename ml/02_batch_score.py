# Databricks notebook source
# MAGIC %md # FreshGroove — Batch Score All SKUs
# MAGIC Loads @prod models and scores every row in gold_waste_risk_features.
# MAGIC Writes results to gold.waste_risk_scores.

# COMMAND ----------
%pip install scikit-learn mlflow
dbutils.library.restartPython()

# COMMAND ----------
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from pyspark.sql import functions as F

CATALOG = "matt_fe_bar_catalog"
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------
waste_model  = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.waste_classifier@prod")
demand_model = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.demand_forecast@prod")
sup_model    = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.supplier_reliability@prod")
print("All 3 @prod models loaded")

# COMMAND ----------
df = spark.table(f"{CATALOG}.gold.gold_waste_risk_features").toPandas()
sup_df = spark.table(f"{CATALOG}.gold.gold_supplier_risk").toPandas()
df = df.merge(sup_df[["supplier_id","late_rate","avg_spoilage_rate"]], on="supplier_id", how="left")
df["late_rate"]         = df["late_rate"].fillna(0.05)
df["avg_spoilage_rate"] = df["avg_spoilage_rate"].fillna(0.10)

le_cat = LabelEncoder().fit(df["category"].fillna("unknown"))
le_reg = LabelEncoder().fit(df["region"].fillna("unknown"))
le_sup = LabelEncoder().fit(df["supplier_id"].fillna("unknown"))

df["category_enc"] = le_cat.transform(df["category"].fillna("unknown"))
df["region_enc"]   = le_reg.transform(df["region"].fillna("unknown"))
df["supplier_enc"] = le_sup.transform(df["supplier_id"].fillna("unknown"))
df["temp_ok_enc"]  = (df["warehouse_temp_ok"].astype(str).str.lower() == "true").astype(int)

FEATURES = ["on_hand_units","units_sold","spoilage_30d_avg","sales_7d_avg",
            "days_to_season_peak","category_enc","region_enc","supplier_enc","temp_ok_enc"]
FEATURES_SUP = FEATURES + ["avg_spoilage_rate"]

X     = df[FEATURES].fillna(0)
X_sup = df[FEATURES_SUP].fillna(0)

# COMMAND ----------
import numpy as np
df["waste_risk_score"]      = waste_model.predict_proba(X)[:, 1]
df["demand_forecast_units"] = demand_model.predict(X).clip(0)
df["supplier_risk_score"]   = sup_model.predict(X_sup).clip(0, 1)

df["risk_tier"] = df["waste_risk_score"].apply(
    lambda s: "HIGH" if s >= 0.70 else ("MEDIUM" if s >= 0.40 else "LOW"))

def recommend(row):
    if row["risk_tier"] == "HIGH":
        reduction = max(10, int(row["on_hand_units"] * 0.25))
        sup = row["supplier_id"]
        alt = "SUP-0007" if sup in ("SUP-0001","SUP-0002","SUP-0003") else "current supplier"
        return f"Reduce order by {reduction} units. Consider backup supplier {alt} for high-risk window."
    elif row["risk_tier"] == "MEDIUM":
        return "Monitor closely. Consider reducing order by 10% if spoilage trend continues."
    else:
        return "No action needed. Continue standard replenishment."

df["recommended_action"] = df.apply(recommend, axis=1)
print(f"Scored {len(df):,} rows")
print(df["risk_tier"].value_counts())

# COMMAND ----------
score_df = spark.createDataFrame(df[[
    "date","store_id","sku_id","sku_name","category","region","supplier_id",
    "on_hand_units","waste_risk_score","demand_forecast_units","supplier_risk_score",
    "risk_tier","recommended_action","spoilage_pct","sales_7d_avg","spoilage_30d_avg"
]])
score_df.write.format("delta").mode("overwrite") \
    .option("overwriteSchema","true") \
    .saveAsTable(f"{CATALOG}.gold.waste_risk_scores")

row_count  = spark.table(f"{CATALOG}.gold.waste_risk_scores").count()
high_count = spark.table(f"{CATALOG}.gold.waste_risk_scores").filter("risk_tier='HIGH'").count()
med_count  = spark.table(f"{CATALOG}.gold.waste_risk_scores").filter("risk_tier='MEDIUM'").count()
print(f"waste_risk_scores written: {row_count:,} rows")
print(f"HIGH: {high_count:,} | MEDIUM: {med_count:,}")

display(spark.table(f"{CATALOG}.gold.waste_risk_scores")
    .filter("risk_tier='HIGH'")
    .select("store_id","sku_id","waste_risk_score","risk_tier","recommended_action","on_hand_units")
    .orderBy("waste_risk_score", ascending=False)
    .limit(5))
