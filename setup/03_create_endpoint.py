#!/usr/bin/env python3
"""Creates the waste_classifier serving endpoint. Stdlib only."""
import json, urllib.request, subprocess, time, sys
sys.path.insert(0, "/Users/matthew.walding/freshgroove-febar")
from setup.token_helper import get_token

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
CATALOG   = "matt_fe_bar_catalog"

token = get_token(PROFILE)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get @prod version
def uc_api(path, method="GET", data=None):
    req = urllib.request.Request(
        f"{WORKSPACE}/api/2.0/mlflow/unity-catalog/{path}",
        data=json.dumps(data).encode() if data else None,
        headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()

uc_name = f"{CATALOG}.ml.waste_classifier"
result, err = uc_api(f"registered-models/alias?name={uc_name}&alias=prod")
if err:
    print(f"Could not get alias: {err[:100]}. Using version 1.")
    version = "1"
else:
    version = result.get("model_version", {}).get("version", "1")
print(f"Using waste_classifier @prod = version {version}")

# Check if endpoint already exists
check_req = urllib.request.Request(
    f"{WORKSPACE}/api/2.0/serving-endpoints/freshgroove-waste-scorer",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    with urllib.request.urlopen(check_req) as r:
        existing = json.loads(r.read())
        state = existing.get("state", {})
        print(f"Endpoint already exists. State: {state}")
        print(f"MODEL_ENDPOINT=freshgroove-waste-scorer")
        sys.exit(0)
except urllib.error.HTTPError as e:
    if e.code != 404:
        print(f"Check error: {e.read().decode()[:100]}")

# Create endpoint
endpoint_config = {
    "name": "freshgroove-waste-scorer",
    "config": {
        "served_models": [{
            "model_name": f"{CATALOG}.ml.waste_classifier",
            "model_version": version,
            "workload_size": "Small",
            "scale_to_zero_enabled": True
        }]
    }
}

req = urllib.request.Request(
    f"{WORKSPACE}/api/2.0/serving-endpoints",
    data=json.dumps(endpoint_config).encode(),
    headers=headers, method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Endpoint created: {result.get('name')}")
        print(f"Initial state: {result.get('state')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error creating endpoint: {body[:300]}")
    sys.exit(1)

print("Endpoint creation submitted. Polling for READY state (up to 10 min)...")
for i in range(60):
    time.sleep(10)
    poll = urllib.request.Request(
        f"{WORKSPACE}/api/2.0/serving-endpoints/freshgroove-waste-scorer",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(poll) as r:
        status = json.loads(r.read())
    state = status.get("state", {}).get("ready", "")
    config_state = status.get("state", {}).get("config_update", "")
    if i % 3 == 0:
        print(f"  [{i*10}s] ready={state}, config={config_state}")
    if state == "READY":
        print("Endpoint is READY.")
        print(f"MODEL_ENDPOINT=freshgroove-waste-scorer")
        break
    if state == "NOT_READY" and config_state == "IN_PROGRESS":
        continue  # still loading
else:
    print("Endpoint still loading after 10 min — check workspace UI")
