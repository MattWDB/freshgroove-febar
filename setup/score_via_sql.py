#!/usr/bin/env python3
"""Creates waste_risk_scores table via SQL warehouse. Stdlib only."""
import json, urllib.request, sys, time
sys.path.insert(0, "/Users/matthew.walding/freshgroove-febar")
from setup.token_helper import get_token

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
WH        = "13d586337d2fb9b5"

token = get_token(PROFILE)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def sql(q):
    payload = {"statement": q, "warehouse_id": WH, "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"}
    req = urllib.request.Request(
        f"{WORKSPACE}/api/2.0/sql/statements",
        data=json.dumps(payload).encode(),
        headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:300]}"

    stmt_id = result.get("statement_id")
    for _ in range(120):
        state = result.get("status", {}).get("state", "")
        if state in ("SUCCEEDED", "FAILED", "CANCELED", "CLOSED"):
            break
        time.sleep(5)
        poll = urllib.request.Request(
            f"{WORKSPACE}/api/2.0/sql/statements/{stmt_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(poll) as r:
            result = json.loads(r.read())

    err = result.get("status", {}).get("error", {})
    if err:
        return None, err.get("message", "")[:400]
    rows = result.get("result", {}).get("data_array", [])
    return rows, None

# Step 1: Create the scored table
print("Creating waste_risk_scores...")
CREATE = (
    "CREATE OR REPLACE TABLE matt_fe_bar_catalog.gold.waste_risk_scores AS "
    "SELECT f.date, f.store_id, f.sku_id, REPLACE(REPLACE(f.sku_id,'SKU-',''),'_',' ') AS sku_name, f.category, f.region, f.supplier_id, f.on_hand_units, "
    "LEAST(1.0, GREATEST(0.0, "
    "COALESCE(f.spoilage_30d_avg, 0.10) * 0.5 + "
    "COALESCE(s.late_rate, 0.05) * 0.3 + "
    "CASE WHEN CAST(f.warehouse_temp_ok AS STRING) = 'false' THEN 0.15 ELSE 0.0 END + "
    "CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast' AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END "
    ")) AS waste_risk_score, "
    "COALESCE(f.sales_7d_avg, CAST(f.units_sold AS DOUBLE), 0.0) AS demand_forecast_units, "
    "COALESCE(s.late_rate, 0.05) AS supplier_risk_score, "
    "CASE "
    "WHEN COALESCE(f.spoilage_30d_avg, 0.0) * 0.5 + COALESCE(s.late_rate, 0.0) * 0.3 + "
    "CASE WHEN f.warehouse_temp_ok = 'false' THEN 0.15 ELSE 0.0 END + "
    "CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast' AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END >= 0.15 THEN 'HIGH' "
    "WHEN COALESCE(f.spoilage_30d_avg, 0.0) * 0.5 + COALESCE(s.late_rate, 0.0) * 0.3 + "
    "CASE WHEN f.warehouse_temp_ok = 'false' THEN 0.15 ELSE 0.0 END + "
    "CASE WHEN f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast' AND MONTH(f.date) = 4 THEN 0.20 ELSE 0.0 END >= 0.08 THEN 'MEDIUM' "
    "ELSE 'LOW' END AS risk_tier, "
    "CASE "
    "WHEN COALESCE(s.late_rate, 0.0) > 0.20 AND f.sku_id = 'SKU-STRWBRY' AND f.region = 'Northeast' "
    "THEN CONCAT('Reduce order by ', CAST(CAST(f.on_hand_units * 0.25 AS INT) AS STRING), ' units. Consider backup supplier SUP-0007.') "
    "WHEN COALESCE(f.spoilage_30d_avg, 0.0) > 0.12 "
    "THEN CONCAT('Reduce order by ', CAST(CAST(f.on_hand_units * 0.20 AS INT) AS STRING), ' units. Spoilage trending above 12%.') "
    "WHEN COALESCE(s.late_rate, 0.0) > 0.18 THEN 'Monitor supplier delivery. Late rate above 18%.' "
    "WHEN f.warehouse_temp_ok = 'false' THEN 'Check refrigeration. Temperature failure detected.' "
    "ELSE 'No action needed. Continue standard replenishment.' "
    "END AS recommended_action, "
    "f.spoilage_pct, f.sales_7d_avg, f.spoilage_30d_avg "
    "FROM matt_fe_bar_catalog.gold.gold_waste_risk_features f "
    "LEFT JOIN matt_fe_bar_catalog.gold.gold_supplier_risk s ON f.supplier_id = s.supplier_id"
)

rows, err = sql(CREATE)
if err:
    print(f"ERROR: {err}")
    sys.exit(1)
print("Table created.")

# Step 2: Count by tier
rows2, err2 = sql(
    "SELECT risk_tier, COUNT(*) as n, ROUND(AVG(waste_risk_score),3) as avg_score "
    "FROM matt_fe_bar_catalog.gold.waste_risk_scores "
    "GROUP BY risk_tier ORDER BY n DESC"
)
print("\nRisk tier distribution:")
for r in (rows2 or []):
    print(f"  tier={r[0]}, count={r[1]}, avg_score={r[2]}")

# Step 3: Sample HIGH risk
rows3, err3 = sql(
    "SELECT store_id, sku_id, ROUND(waste_risk_score,3) as score, risk_tier, "
    "LEFT(recommended_action, 70) as action "
    "FROM matt_fe_bar_catalog.gold.waste_risk_scores "
    "WHERE risk_tier='HIGH' ORDER BY waste_risk_score DESC LIMIT 5"
)
print("\nTop HIGH risk rows:")
for r in (rows3 or []):
    print(f"  {r}")

# Step 4: Total count
rows4, _ = sql("SELECT COUNT(*) FROM matt_fe_bar_catalog.gold.waste_risk_scores")
total = rows4[0][0] if rows4 else "?"
print(f"\nTotal rows: {total}")
print("waste_risk_scores created successfully.")
