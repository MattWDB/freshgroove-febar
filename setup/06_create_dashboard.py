#!/usr/bin/env python3
"""Creates FreshGroove Waste Risk Control Tower dashboard. Stdlib only."""
import json, urllib.request, subprocess, sys

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
WAREHOUSE = "13d586337d2fb9b5"
CATALOG   = "matt_fe_bar_catalog"

result = subprocess.run(["databricks", "auth", "token", "--profile", PROFILE], capture_output=True, text=True)
TOKEN = json.loads(result.stdout).get("access_token", result.stdout.strip())
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

MAX_DATE_SUBQ = f"(SELECT MAX(date) FROM {CATALOG}.gold.gold_waste_risk_features)"

dashboard_payload = {
    "display_name": "FreshGroove Waste Risk Control Tower",
    "warehouse_id": WAREHOUSE,
    "serialized_dashboard": json.dumps({
        "pages": [{
            "name": "page1",
            "display_name": "Waste Risk Overview",
            "layout": [],
            "widgets": [
                {
                    "name": "kpi_waste_rate",
                    "title": "Waste Rate (Last 30 Days)",
                    "textbox_spec": "",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE, "query_id": "",
                        "query": f"SELECT ROUND(AVG(spoilage_pct)*100,1) as `Waste Rate %` FROM {CATALOG}.gold.gold_waste_risk_features WHERE date >= {MAX_DATE_SUBQ} - INTERVAL 30 DAYS"}}]
                },
                {
                    "name": "kpi_high_risk_count",
                    "title": "High-Risk SKUs (Last 7 Days)",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE,
                        "query": f"SELECT COUNT(*) as `High Risk SKUs` FROM {CATALOG}.gold.waste_risk_scores WHERE risk_tier='HIGH' AND date >= {MAX_DATE_SUBQ} - INTERVAL 7 DAYS"}}]
                },
                {
                    "name": "trend_waste_by_month",
                    "title": "Waste Rate by Month (with April Strawberry Spike)",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE,
                        "query": f"SELECT DATE_TRUNC('month', date) as Month, ROUND(AVG(spoilage_pct)*100,1) as `Waste Rate %` FROM {CATALOG}.gold.gold_waste_risk_features GROUP BY 1 ORDER BY 1"}}]
                },
                {
                    "name": "bar_supplier_risk",
                    "title": "Worst Suppliers by Spoilage Rate",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE,
                        "query": f"SELECT supplier_id, avg_spoilage_pct as `Avg Spoilage %` FROM {CATALOG}.gold.v_supplier_risk_summary ORDER BY avg_spoilage_pct DESC LIMIT 7"}}]
                },
                {
                    "name": "bar_store_risk",
                    "title": "High-Risk SKUs by Store (Last 7 Days)",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE,
                        "query": f"SELECT store_id, COUNT(*) as `High Risk Count` FROM {CATALOG}.gold.waste_risk_scores WHERE risk_tier='HIGH' AND date >= {MAX_DATE_SUBQ} - INTERVAL 7 DAYS GROUP BY 1 ORDER BY 2 DESC"}}]
                },
                {
                    "name": "table_top_risks",
                    "title": "Top 10 Waste Risks This Week",
                    "queries": [{"name": "main_query", "query": {"warehouse_id": WAREHOUSE,
                        "query": f"SELECT store_id, sku_id, region, supplier_id, ROUND(waste_risk_score,3) as risk_score, risk_tier, recommended_action FROM {CATALOG}.gold.waste_risk_scores WHERE risk_tier='HIGH' AND date >= {MAX_DATE_SUBQ} - INTERVAL 7 DAYS ORDER BY waste_risk_score DESC LIMIT 10"}}]
                }
            ]
        }]
    })
}

for api_path in ["/api/2.0/lakeview/dashboards", "/api/2.0/dashboards"]:
    req = urllib.request.Request(
        f"{WORKSPACE}{api_path}",
        data=json.dumps(dashboard_payload).encode(),
        headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            dashboard_id = result.get("dashboard_id") or result.get("id")
            print(f"Dashboard created via {api_path}: {dashboard_id}")
            print(f"URL: {WORKSPACE}/dashboards/{dashboard_id}")
            with open(".env.local", "a") as f:
                f.write(f"\nDASHBOARD_ID={dashboard_id}\n")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        print(f"{api_path} -> HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        print(f"{api_path} -> {e}")

# Try CLI
cli = subprocess.run(
    ["databricks", "dashboards", "create",
     "--display-name", "FreshGroove Waste Risk Control Tower",
     "--warehouse-id", WAREHOUSE, "--profile", PROFILE],
    capture_output=True, text=True
)
if cli.returncode == 0:
    print(cli.stdout)
else:
    print(f"CLI error: {cli.stderr[:200]}")
    print("Manual creation required - see printed SQL queries above.")
