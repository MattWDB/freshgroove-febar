#!/usr/bin/env python3
"""Creates the FreshGroove Genie space via REST API. Stdlib only."""
import json, urllib.request, subprocess, sys

PROFILE      = "fe-bar"
WORKSPACE    = "https://fevm-matt-fe-bar.cloud.databricks.com"
WAREHOUSE_ID = "13d586337d2fb9b5"

result = subprocess.run(["databricks", "auth", "token", "--profile", PROFILE], capture_output=True, text=True)
token_data = json.loads(result.stdout)
TOKEN = token_data.get("access_token") or token_data.get("token_value") or result.stdout.strip()
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

with open("genie/space_instructions.md") as f:
    instructions = f.read()

space_config = {
    "title": "FreshGroove — Perishable Ops Intelligence",
    "description": "Ask questions about perishable waste risk, supplier reliability, and OTIF performance.",
    "warehouse_id": WAREHOUSE_ID,
    "table_identifiers": [
        "matt_fe_bar_catalog.gold.gold_waste_risk_features",
        "matt_fe_bar_catalog.gold.waste_risk_scores",
        "matt_fe_bar_catalog.gold.gold_supplier_risk",
        "matt_fe_bar_catalog.gold.reorder_queue",
        "matt_fe_bar_catalog.gold.v_waste_kpis",
        "matt_fe_bar_catalog.gold.v_high_risk_skus",
        "matt_fe_bar_catalog.gold.v_supplier_risk_summary"
    ],
    "instructions": instructions
}

for endpoint in ["/api/2.0/genie/spaces", "/api/2.0/aibi/genie-spaces"]:
    req = urllib.request.Request(
        f"{WORKSPACE}{endpoint}",
        data=json.dumps(space_config).encode(),
        headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            space_id = result.get("space_id") or result.get("id") or result.get("genie_space_id")
            print(f"Genie space created via {endpoint}: {space_id}")
            print(f"Add to .env.local: GENIE_SPACE_ID={space_id}")
            print(json.dumps(result, indent=2)[:500])
            sys.exit(0)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"{endpoint} → HTTP {e.code}: {body[:300]}")
    except Exception as e:
        print(f"{endpoint} → Error: {e}")

print("\nGenie space API not available via REST. Trying CLI...")
cli_result = subprocess.run(
    ["databricks", "genie", "spaces", "create",
     "--title", "FreshGroove — Perishable Ops Intelligence",
     "--warehouse-id", WAREHOUSE_ID,
     "--profile", PROFILE],
    capture_output=True, text=True
)
if cli_result.returncode == 0:
    print(f"CLI result: {cli_result.stdout}")
else:
    print(f"CLI error: {cli_result.stderr[:300]}")
    print("\nManual creation required:")
    print(f"1. Navigate to {WORKSPACE}/genie")
    print("2. Click 'New' -> 'Genie Space'")
    print("3. Title: 'FreshGroove — Perishable Ops Intelligence'")
    print("4. Add tables: matt_fe_bar_catalog.gold.{waste_risk_scores, gold_waste_risk_features, gold_supplier_risk, reorder_queue, v_waste_kpis, v_high_risk_skus, v_supplier_risk_summary}")
    print("5. Paste instructions from genie/space_instructions.md")
    print("6. Save and copy the space ID from the URL")
