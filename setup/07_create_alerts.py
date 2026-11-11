#!/usr/bin/env python3
"""Creates 2 SQL alerts for FreshGroove. Stdlib only."""
import json, urllib.request, subprocess, sys

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
WAREHOUSE = "13d586337d2fb9b5"
CATALOG   = "matt_fe_bar_catalog"

result = subprocess.run(["databricks", "auth", "token", "--profile", PROFILE], capture_output=True, text=True)
TOKEN = json.loads(result.stdout).get("access_token", result.stdout.strip())
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

MAX_DATE_SUBQ = f"(SELECT MAX(date) FROM {CATALOG}.gold.gold_waste_risk_features)"

alerts = [
    {
        "display_name": "FreshGroove: Waste Rate > 10%",
        "condition": {
            "op": "GREATER_THAN",
            "operand": {"column": {"name": "waste_rate_pct"}},
            "threshold": {"value": {"double_value": 10.0}}
        },
        "query_text": f"SELECT ROUND(AVG(spoilage_pct)*100,1) as waste_rate_pct FROM {CATALOG}.gold.gold_waste_risk_features WHERE date >= {MAX_DATE_SUBQ} - INTERVAL 7 DAYS",
        "warehouse_id": WAREHOUSE,
        "schedule": {"quartz_cron_schedule": "0 0 8 * * ?", "timezone_id": "US/Eastern"},
        "notification_subscriptions": [{"user_email": "matthew.walding@databricks.com"}]
    },
    {
        "display_name": "FreshGroove: High-Risk SKU Count > 50",
        "condition": {
            "op": "GREATER_THAN",
            "operand": {"column": {"name": "high_risk_count"}},
            "threshold": {"value": {"double_value": 50.0}}
        },
        "query_text": f"SELECT COUNT(*) as high_risk_count FROM {CATALOG}.gold.waste_risk_scores WHERE risk_tier='HIGH' AND date >= {MAX_DATE_SUBQ} - INTERVAL 7 DAYS",
        "warehouse_id": WAREHOUSE,
        "schedule": {"quartz_cron_schedule": "0 0 8 * * ?", "timezone_id": "US/Eastern"},
        "notification_subscriptions": [{"user_email": "matthew.walding@databricks.com"}]
    }
]

alert_ids = []
for alert in alerts:
    created = False
    for endpoint in ["/api/2.0/sql/alerts-v2", "/api/2.0/sql/alerts"]:
        req = urllib.request.Request(
            f"{WORKSPACE}{endpoint}",
            data=json.dumps(alert).encode(),
            headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                r = json.loads(resp.read())
                aid = r.get("id") or r.get("alert_id")
                print(f"Alert created: {aid} -- {alert['display_name']}")
                alert_ids.append(str(aid))
                created = True
                break
        except urllib.error.HTTPError as e:
            print(f"{endpoint} -> HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"{endpoint} -> {e}")
    if not created:
        print(f"Could not create alert: {alert['display_name']}")

if alert_ids:
    with open(".env.local", "a") as f:
        f.write(f"\nALERT_IDS={','.join(alert_ids)}\n")
    print(f"Alert IDs: {alert_ids}")
else:
    print("No alerts created via API.")
