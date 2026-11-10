# Databricks notebook source
# MAGIC %md # FreshGroove — Batch Score v2 (no restart)
# MAGIC Scores all SKUs using rule-based + model heuristics.
# MAGIC Writes results to gold.waste_risk_scores.

# COMMAND ----------
# Install in a way that doesn't require restart
import subprocess
subprocess.run(["pip", "install", "scikit-learn", "mlflow", "--quiet"], capture_output=True)

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from pyspark.sql import functions as F, types as T

CATALOG = "matt_fe_bar_catalog"
mlflow.set_registry_uri("databricks-uc")

print("Loading models...")
try:
    waste_model  = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.waste_classifier@prod")
    demand_model = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.demand_forecast@prod")
    sup_model    = mlflow.sklearn.load_model(f"models:/{CATALOG}.ml.supplier_reliability@prod")
    USE_ML = True
    print("All 3 @prod models loaded via registry")
except Exception as e:
    print(f"Registry load failed: {e}. Using artifact URIs...")
    try:
        waste_model  = mlflow.sklearn.load_model("dbfs:/databricks/mlflow-tracking/2198757363928003/98cf38d7e2be493b947e78d778c81ce3/artifacts/model")
        demand_model = mlflow.sklearn.load_model("dbfs:/databricks/mlflow-tracking/2198757363928003/794941398a764588b269166456e01b2c/artifacts/model")
        sup_model    = mlflow.sklearn.load_model("dbfs:/databricks/mlflow-tracking/2198757363928003/240036b3334640e89852d0c1d33d1ac9/artifacts/model")
        USE_ML = True
        print("Models loaded via artifact URIs")
    except Exception as e2:
        print(f"Artifact load also failed: {e2}. Will use rule-based scoring.")
        USE_ML = False

# COMMAND ----------
# Load features
df = spark.table(f"{CATALOG}.gold.gold_waste_risk_features").toPandas()
sup_df = spark.table(f"{CATALOG}.gold.gold_supplier_risk").toPandas()
df = df.merge(sup_df[["supplier_id","late_rate","avg_spoilage_rate"]], on="supplier_id", how="left")
df["late_rate"]         = df["late_rate"].fillna(0.05)
df["avg_spoilage_rate"] = df["avg_spoilage_rate"].fillna(0.10)

df["category_enc"] = LabelEncoder().fit_transform(df["category"].fillna("unknown"))
df["region_enc"]   = LabelEncoder().fit_transform(df["region"].fillna("unknown"))
df["supplier_enc"] = LabelEncoder().fit_transform(df["supplier_id"].fillna("unknown"))
df["temp_ok_enc"]  = (df["warehouse_temp_ok"].astype(str).str.lower() == "true").astype(int)

FEATURES = ["on_hand_units","units_sold","spoilage_30d_avg","sales_7d_avg",
            "days_to_season_peak","category_enc","region_enc","supplier_enc","temp_ok_enc"]
FEATURES_SUP = FEATURES + ["avg_spoilage_rate"]

X     = df[FEATURES].fillna(0)
X_sup = df[FEATURES_SUP].fillna(0)
print(f"Features loaded: {len(df):,} rows")

# COMMAND ----------
if USE_ML:
    df["waste_risk_score"]      = waste_model.predict_proba(X)[:, 1]
    df["demand_forecast_units"] = demand_model.predict(X).clip(0)
    df["supplier_risk_score"]   = sup_model.predict(X_sup).clip(0, 1)
    print("Scored with ML models")
else:
    # Rule-based fallback: combine spoilage_30d_avg, late_rate, temp signal
    df["waste_risk_score"] = (
        df["spoilage_30d_avg"] * 0.6 +
        df["late_rate"] * 0.3 +
        (1 - df["temp_ok_enc"]) * 0.1
    ).clip(0, 1)
    df["demand_forecast_units"] = df["sales_7d_avg"].clip(0)
    df["supplier_risk_score"]   = df["late_rate"].clip(0, 1)
    print("Scored with rule-based fallback")

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
print(f"Risk tier distribution:\n{df['risk_tier'].value_counts()}")

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

# Show sample
display(spark.table(f"{CATALOG}.gold.waste_risk_scores")
    .filter("risk_tier='HIGH'")
    .select("store_id","sku_id","waste_risk_score","risk_tier","recommended_action")
    .orderBy("waste_risk_score", ascending=False)
    .limit(5))
