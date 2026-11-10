#!/usr/bin/env python3
"""Adds column descriptions to UC tables for Genie accuracy. Stdlib only."""
import subprocess, sys, json, urllib.request

PROFILE      = "fe-bar"
WAREHOUSE_ID = sys.argv[1] if len(sys.argv) > 1 else "13d586337d2fb9b5"
CATALOG      = "matt_fe_bar_catalog"
WORKSPACE    = "https://fevm-matt-fe-bar.cloud.databricks.com"

result = subprocess.run(
    ["databricks", "auth", "token", "--profile", PROFILE],
    capture_output=True, text=True
)
raw = result.stdout.strip()
try:
    token = json.loads(raw).get("access_token", raw)
except Exception:
    token = raw

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def sql(statement):
    body = json.dumps({"statement": statement, "warehouse_id": WAREHOUSE_ID, "wait_timeout": "30s"}).encode()
    req = urllib.request.Request(
        f"{WORKSPACE}/api/2.0/sql/statements",
        data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            d = json.loads(resp.read())
        status = d.get("status", {}).get("state", "?")
        if status == "SUCCEEDED":
            print(f"OK: {statement[:80]}...")
        else:
            err = d.get("status", {}).get("error", {}).get("message", "")[:200]
            print(f"SKIP ({status}): {statement[:60]}... | {err}")
    except Exception as e:
        print(f"ERR: {statement[:60]}... | {e}")

# Table comments
sql(f"COMMENT ON TABLE {CATALOG}.gold.gold_waste_risk_features IS 'ML feature table. One row per store/SKU/date with all signals for waste risk scoring. Source of truth for waste_classifier, demand_forecast, and supplier_reliability models.'")
sql(f"COMMENT ON TABLE {CATALOG}.gold.gold_kpi_summary IS 'Business KPI summary: avg_waste_rate, total_spoilage_cost_usd, otif_rate, chargeback_cost_usd. Read by app Overview tab and Genie Agent.'")
sql(f"COMMENT ON TABLE {CATALOG}.gold.gold_supplier_risk IS 'Supplier reliability metrics: late_rate and avg_spoilage_rate per supplier. Feeds supplier_reliability ML model and Genie queries.'")

# Column descriptions
col_comments = [
    (f"{CATALOG}.gold.gold_waste_risk_features", "spoilage_pct", "Fraction of on_hand_units that expired unsold. Formula: spoilage_units / on_hand_units. Target: < 0.06 (6%). Current avg: ~0.12 (12%)."),
    (f"{CATALOG}.gold.gold_waste_risk_features", "is_high_risk", "Binary label: 1 if spoilage_pct > 0.12 (above average), 0 otherwise. Training target for waste_classifier model."),
    (f"{CATALOG}.gold.gold_waste_risk_features", "sales_7d_avg", "Rolling 7-day average units sold for this store+SKU combination. Demand signal for the waste and demand models."),
    (f"{CATALOG}.gold.gold_waste_risk_features", "spoilage_30d_avg", "Rolling 30-day average spoilage rate for this store+SKU. Trend signal — rising rate indicates systemic issue."),
    (f"{CATALOG}.gold.gold_waste_risk_features", "days_to_season_peak", "Days until April 15 seasonal demand peak (strawberry season). Negative = past peak. Used by demand_forecast model."),
    (f"{CATALOG}.gold.gold_supplier_risk", "late_rate", "Fraction of deliveries where units_received < 95% of units_ordered. Rising late_rate indicates unreliable supplier. Threshold for HIGH risk: > 0.20."),
    (f"{CATALOG}.gold.gold_kpi_summary", "avg_waste_rate", "Portfolio-level average spoilage rate across all stores and SKUs. Displayed as 'Waste Rate' KPI in app Overview."),
    (f"{CATALOG}.gold.gold_kpi_summary", "total_spoilage_cost_usd", "Estimated annual spoilage cost in USD. Formula: sum(spoilage_units * $45 unit value). Displayed as 'Spoilage Cost/yr' KPI."),
    (f"{CATALOG}.gold.gold_kpi_summary", "otif_rate", "On-Time In-Full delivery rate. Current: 0.91 (91%). Retailer threshold: 0.98 (98%). Below threshold triggers 3% chargeback penalty."),
    (f"{CATALOG}.gold.gold_kpi_summary", "chargeback_cost_usd", "Estimated annual cost of OTIF chargebacks from retail partners. Current: ~$1.5M/year at 91% OTIF."),
]

for table, col, comment in col_comments:
    safe_comment = comment.replace("'", "''")
    sql(f"ALTER TABLE {table} ALTER COLUMN {col} COMMENT '{safe_comment}'")

print("UC governance complete.")
