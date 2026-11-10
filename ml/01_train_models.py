# Databricks notebook source
# MAGIC %md # FreshGroove — Train 3 ML Models
# MAGIC Trains waste_classifier, demand_forecast, and supplier_reliability.
# MAGIC Registers all three to Unity Catalog with @prod alias.

# COMMAND ----------
%pip install scikit-learn mlflow
dbutils.library.restartPython()

# COMMAND ----------
import mlflow
import mlflow.sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
import numpy as np

CATALOG = "matt_fe_bar_catalog"
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Users/matthew.walding@databricks.com/freshgroove-febar-ml")

# COMMAND ----------
# Load gold features
df = spark.table(f"{CATALOG}.gold.gold_waste_risk_features").toPandas()
print(f"Features loaded: {len(df):,} rows, {df.shape[1]} columns")
print(df.dtypes)
print(df.isnull().sum())

# COMMAND ----------
# ── Model 1: waste_classifier (binary: is_high_risk) ──────────────────────
print("\n=== Training waste_classifier ===")

FEATURES_CLASS = ["on_hand_units", "units_sold", "spoilage_30d_avg",
                  "sales_7d_avg", "days_to_season_peak"]

le_cat  = LabelEncoder()
le_reg  = LabelEncoder()
le_sup  = LabelEncoder()

df["category_enc"]  = le_cat.fit_transform(df["category"].fillna("unknown"))
df["region_enc"]    = le_reg.fit_transform(df["region"].fillna("unknown"))
df["supplier_enc"]  = le_sup.fit_transform(df["supplier_id"].fillna("unknown"))
df["temp_ok_enc"]   = (df["warehouse_temp_ok"].astype(str).str.lower() == "true").astype(int)

FEATURES_CLASS_ALL = FEATURES_CLASS + ["category_enc", "region_enc", "supplier_enc", "temp_ok_enc"]

X_cls = df[FEATURES_CLASS_ALL].fillna(0)
y_cls = df["is_high_risk"].fillna(0).astype(int)

X_tr, X_te, y_tr, y_te = train_test_split(X_cls, y_cls, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="waste_classifier_v1") as run:
    model_cls = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, max_depth=6,
        class_weight="balanced", random_state=42
    )
    model_cls.fit(X_tr, y_tr)
    y_prob = model_cls.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, y_prob)
    mlflow.log_params({"max_iter": 200, "learning_rate": 0.05, "class_weight": "balanced"})
    mlflow.log_metric("auc", auc)
    mlflow.log_metric("train_rows", len(X_tr))
    mlflow.sklearn.log_model(
        model_cls, "model",
        registered_model_name=f"{CATALOG}.ml.waste_classifier",
        input_example=X_tr.head(5)
    )
    run_id_cls = run.info.run_id
    print(f"waste_classifier AUC: {auc:.4f} | run_id: {run_id_cls}")

client = mlflow.tracking.MlflowClient()
versions = client.search_model_versions(f"name='{CATALOG}.ml.waste_classifier'")
latest_cls = max(versions, key=lambda v: int(v.version))
client.set_registered_model_alias(f"{CATALOG}.ml.waste_classifier", "prod", latest_cls.version)
print(f"waste_classifier @prod = version {latest_cls.version}")

# COMMAND ----------
# ── Model 2: demand_forecast (regressor: units_sold) ──────────────────────
print("\n=== Training demand_forecast ===")

X_dmnd = df[FEATURES_CLASS_ALL].fillna(0)
y_dmnd = df["units_sold"].fillna(0).astype(float)

X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_dmnd, y_dmnd, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="demand_forecast_v1") as run:
    model_dmnd = HistGradientBoostingRegressor(
        max_iter=200, learning_rate=0.05, max_depth=5, random_state=42
    )
    model_dmnd.fit(X_tr2, y_tr2)
    y_pred2 = model_dmnd.predict(X_te2)
    rmse2 = float(np.sqrt(mean_squared_error(y_te2, y_pred2)))
    r2_2  = float(r2_score(y_te2, y_pred2))
    mlflow.log_params({"max_iter": 200, "learning_rate": 0.05})
    mlflow.log_metric("rmse", rmse2)
    mlflow.log_metric("r2", r2_2)
    mlflow.sklearn.log_model(
        model_dmnd, "model",
        registered_model_name=f"{CATALOG}.ml.demand_forecast",
        input_example=X_tr2.head(5)
    )
    print(f"demand_forecast RMSE: {rmse2:.2f} | R2: {r2_2:.4f}")

client.set_registered_model_alias(f"{CATALOG}.ml.demand_forecast", "prod",
    max(client.search_model_versions(f"name='{CATALOG}.ml.demand_forecast'"),
        key=lambda v: int(v.version)).version)
print("demand_forecast @prod set")

# COMMAND ----------
# ── Model 3: supplier_reliability (regressor: late_rate) ──────────────────
print("\n=== Training supplier_reliability ===")

sup_df = spark.table(f"{CATALOG}.gold.gold_supplier_risk").toPandas()
print(f"Supplier data: {len(sup_df)} rows")

df_sup = df.merge(sup_df[["supplier_id","late_rate","avg_spoilage_rate"]],
                  on="supplier_id", how="left")
df_sup["late_rate"]         = df_sup["late_rate"].fillna(0.05)
df_sup["avg_spoilage_rate"] = df_sup["avg_spoilage_rate"].fillna(0.10)

FEATURES_SUP = FEATURES_CLASS_ALL + ["avg_spoilage_rate"]
X_sup = df_sup[FEATURES_SUP].fillna(0)
y_sup = df_sup["late_rate"].fillna(0.05)

X_tr3, X_te3, y_tr3, y_te3 = train_test_split(X_sup, y_sup, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="supplier_reliability_v1") as run:
    model_sup = HistGradientBoostingRegressor(
        max_iter=150, learning_rate=0.08, max_depth=4, random_state=42
    )
    model_sup.fit(X_tr3, y_tr3)
    y_pred3 = model_sup.predict(X_te3)
    rmse3 = float(np.sqrt(mean_squared_error(y_te3, y_pred3)))
    r2_3  = float(r2_score(y_te3, y_pred3))
    mlflow.log_params({"max_iter": 150, "learning_rate": 0.08})
    mlflow.log_metric("rmse", rmse3)
    mlflow.log_metric("r2",   r2_3)
    mlflow.sklearn.log_model(
        model_sup, "model",
        registered_model_name=f"{CATALOG}.ml.supplier_reliability",
        input_example=X_tr3.head(5)
    )
    print(f"supplier_reliability RMSE: {rmse3:.4f} | R2: {r2_3:.4f}")

client.set_registered_model_alias(f"{CATALOG}.ml.supplier_reliability", "prod",
    max(client.search_model_versions(f"name='{CATALOG}.ml.supplier_reliability'"),
        key=lambda v: int(v.version)).version)
print("supplier_reliability @prod set")

# COMMAND ----------
for name in ["waste_classifier", "demand_forecast", "supplier_reliability"]:
    mv = client.get_model_version_by_alias(f"{CATALOG}.ml.{name}", "prod")
    print(f"{CATALOG}.ml.{name} @prod = version {mv.version}")

print("\nAll 3 models registered with @prod alias. Training complete.")
