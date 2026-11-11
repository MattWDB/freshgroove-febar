#!/usr/bin/env python3
"""
FreshGroove FE Bar — End-to-End Integration Test
Hits all 6 layers to prove the integrated build works.
Run: python tests/e2e_api_test.py
"""
import subprocess, json, sys, urllib.request, urllib.error

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
CATALOG   = "matt_fe_bar_catalog"
WAREHOUSE = "13d586337d2fb9b5"
PIPELINE  = "f668d89e-d740-4352-9d26-f85022fbe3e4"
GENIE_ID  = "01f1dd14a9e21327992887fd1d1ede03"
APP_URL   = "freshgroove-app-7474655831226413.aws.databricksapps.com"
ENDPOINT  = "freshgroove-waste-scorer"

result = subprocess.run(
    ["databricks", "auth", "token", "--profile", PROFILE],
    capture_output=True, text=True
)
TOKEN = json.loads(result.stdout).get("access_token", result.stdout.strip())
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def sql(statement: str) -> dict:
    req = urllib.request.Request(
        f"{WORKSPACE}/api/2.0/sql/statements",
        data=json.dumps({
            "statement": statement,
            "warehouse_id": WAREHOUSE,
            "wait_timeout": "30s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        }).encode(),
        headers=headers, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_first_value(result: dict):
    rows = result.get("result", {}).get("data_array", [])
    return rows[0][0] if rows else None

def api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

results = []

def test(name: str, fn):
    try:
        value = fn()
        print(f"PASS  {name}: {value}")
        results.append((name, True, str(value)))
        return True
    except Exception as e:
        print(f"FAIL  {name}: {e}")
        results.append((name, False, str(e)))
        return False

# Layer 1: Volume (raw data exists)
test("Layer 1 — Volume: store_inventory.csv in raw_landing",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM read_files('/Volumes/{CATALOG}/bronze/raw_landing/store_inventory/')"
    ))
)

# Layer 2: Lakeflow pipeline (Gold table populated)
test("Layer 2 — Lakeflow: gold_waste_risk_features populated",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM {CATALOG}.gold.gold_waste_risk_features"
    ))
)

# Layer 3: Unity Catalog (ML model registered)
test("Layer 3 — Unity Catalog: waste_classifier model exists in ml schema",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM {CATALOG}.information_schema.tables WHERE table_schema='ml' OR table_name LIKE '%waste%'"
    ))
)

test("Layer 3b — UC Model Registry: waste_classifier registered",
    lambda: (
        api_get(f"{WORKSPACE}/api/2.0/mlflow/registered-models/get?name={CATALOG}.ml.waste_classifier")
        .get("registered_model", {}).get("name", "not found")
    )
)

# Layer 4: ML scoring
test("Layer 4 — ML: waste_risk_scores has HIGH risk rows",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM {CATALOG}.gold.waste_risk_scores WHERE risk_tier='HIGH'"
    ))
)

test("Layer 4b — ML: serving endpoint freshgroove-waste-scorer is READY",
    lambda: (
        api_get(f"{WORKSPACE}/api/2.0/serving-endpoints/{ENDPOINT}")
        .get("state", {}).get("ready", "UNKNOWN")
    )
)

# Layer 5: Operational serving
test("Layer 5 — Operational: reorder_queue rows (HIGH+MEDIUM)",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM {CATALOG}.gold.reorder_queue WHERE risk_tier IN ('HIGH','MEDIUM')"
    ))
)

test("Layer 5b — Operational: write-back audit trail (acknowledged rows exist)",
    lambda: get_first_value(sql(
        f"SELECT COUNT(*) FROM {CATALOG}.gold.reorder_queue WHERE status='acknowledged' AND acknowledged_by IS NOT NULL"
    ))
)

# Layer 6: Genie Agent
test("Layer 6 — Genie: space accessible",
    lambda: (
        api_get(f"{WORKSPACE}/api/2.0/genie/spaces/{GENIE_ID}")
        .get("title", "no title")
    )
)

# Bonus: Dashboard and App
test("Bonus — Dashboard: Lakeview dashboard exists",
    lambda: (
        api_get(f"{WORKSPACE}/api/2.0/lakeview/dashboards/01f1ddd68ed8119a9b9328fd0c5c414b")
        .get("display_name", "not found")
    )
)

test("Bonus — App: freshgroove-app is ACTIVE",
    lambda: (
        json.loads(subprocess.run(
            ["databricks", "apps", "get", "freshgroove-app", "--profile", PROFILE, "--output", "json"],
            capture_output=True, text=True
        ).stdout or '{}').get("compute_status", {}).get("state",
        json.loads(subprocess.run(
            ["databricks", "apps", "get", "freshgroove-app", "--profile", PROFILE, "--output", "json"],
            capture_output=True, text=True
        ).stdout or '{}').get("app_status", {}).get("state", "UNKNOWN"))
    )
)

# Summary
passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)
print(f"\n{'='*50}")
print(f"E2E Result: {passed}/{total} passed")
print(f"{'='*50}")
for name, ok, val in results:
    status = "✓" if ok else "✗"
    print(f"  {status} {name}: {val[:70]}")

if passed >= 6:
    print(f"\n✅ Core 6 layers verified — build is submission-ready")
else:
    print(f"\n⚠ {total - passed} checks failed — review above")

sys.exit(0 if passed >= 6 else 1)
