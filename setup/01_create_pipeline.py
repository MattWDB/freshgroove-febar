#!/usr/bin/env python3
"""Creates the Lakeflow SDP pipeline via Databricks REST API. Stdlib only."""
import json, urllib.request, subprocess, sys, time

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
CATALOG   = "matt_fe_bar_catalog"

result = subprocess.run(
    ["databricks", "auth", "token", "--profile", PROFILE],
    capture_output=True, text=True
)
raw = result.stdout.strip()
# Output may be JSON {"access_token": "..."} or plain token string
try:
    token = json.loads(raw).get("access_token", raw)
except Exception:
    token = raw
if not token:
    print("ERROR: could not get auth token"); sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

pipeline_config = {
    "name": "freshgroove-pipeline",
    "catalog": CATALOG,
    "target": "silver",
    "development": True,
    "serverless": True,
    "channel": "CURRENT",
    "libraries": [
        {"notebook": {"path": "/Workspace/Users/matthew.walding@databricks.com/freshgroove-febar/pipelines/01_bronze_ingest"}},
        {"notebook": {"path": "/Workspace/Users/matthew.walding@databricks.com/freshgroove-febar/pipelines/02_silver_clean"}},
        {"notebook": {"path": "/Workspace/Users/matthew.walding@databricks.com/freshgroove-febar/pipelines/03_gold_agg"}}
    ],
    "configuration": {
        "pipelines.enzyme.disabled": "true"
    }
}

req = urllib.request.Request(
    f"{WORKSPACE}/api/2.0/pipelines",
    data=json.dumps(pipeline_config).encode(),
    headers=headers, method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        pipeline_id = result.get("pipeline_id") or result.get("id")
        print(f"Pipeline created: {pipeline_id}")
        print(f"Add to .env.local: PIPELINE_ID={pipeline_id}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body}")
    sys.exit(1)

# Trigger a pipeline update (full refresh)
time.sleep(2)
run_req = urllib.request.Request(
    f"{WORKSPACE}/api/2.0/pipelines/{pipeline_id}/updates",
    data=json.dumps({"full_refresh": True}).encode(),
    headers=headers, method="POST"
)
try:
    with urllib.request.urlopen(run_req) as resp:
        run_result = json.loads(resp.read())
        update_id = run_result.get("update_id")
        print(f"Pipeline update triggered: {update_id}")
        print(f"Monitor at: {WORKSPACE}/pipelines/{pipeline_id}")
except urllib.error.HTTPError as e:
    print(f"Run trigger error: {e.read().decode()}")
    print("Pipeline created. Trigger manually in workspace UI.")
