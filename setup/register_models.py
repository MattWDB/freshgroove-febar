#!/usr/bin/env python3
"""Registers trained models to UC registry and sets @prod alias. Stdlib only."""
import json, urllib.request, sys, time
sys.path.insert(0, "/Users/matthew.walding/freshgroove-febar")
from setup.token_helper import get_token

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"
CATALOG   = "matt_fe_bar_catalog"
EXP_ID    = "2198757363928003"

token = get_token(PROFILE)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

MODELS = {
    "waste_classifier": {
        "run_id": "98cf38d7e2be493b947e78d778c81ce3",
        "artifact_path": "model",
        "metric": "auc=0.7984"
    },
    "demand_forecast": {
        "run_id": "794941398a764588b269166456e01b2c",
        "artifact_path": "model",
        "metric": "r2=0.9999, rmse=0.029"
    },
    "supplier_reliability": {
        "run_id": "240036b3334640e89852d0c1d33d1ac9",
        "artifact_path": "model",
        "metric": "r2=0.9999, rmse=0.00021"
    }
}

def uc_api(path, method="GET", data=None):
    """Call UC MLflow API."""
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

for model_name, info in MODELS.items():
    uc_name = f"{CATALOG}.ml.{model_name}"
    run_id = info["run_id"]
    source = f"dbfs:/databricks/mlflow-tracking/{EXP_ID}/{run_id}/artifacts/{info['artifact_path']}"

    print(f"\n--- {uc_name} ---")

    # Create registered model
    result, err = uc_api("registered-models/create", "POST", {
        "name": uc_name,
        "comment": f"FreshGroove FE Bar - {model_name}. {info['metric']}"
    })
    if err and "RESOURCE_ALREADY_EXISTS" not in err:
        print(f"  Create: {err[:150]}")
    else:
        print(f"  Model created/exists")

    # Get existing versions to find version number
    result_list, _ = uc_api(f"model-versions/search?filter=name%3D%27{uc_name}%27&max_results=10")
    existing = result_list.get("model_versions", []) if result_list else []
    print(f"  Existing versions: {[v.get('version') for v in existing]}")

    # Create new version if needed
    if not existing:
        result2, err2 = uc_api("model-versions/create", "POST", {
            "name": uc_name,
            "source": source,
            "run_id": run_id,
            "comment": f"Trained on 201K rows. {info['metric']}"
        })
        if err2:
            print(f"  Version create error: {err2[:200]}")
            continue
        version = result2.get("model_version", {}).get("version", "1")
        print(f"  Created version: {version}")
    else:
        version = max(existing, key=lambda v: int(v.get("version","0"))).get("version", "1")
        print(f"  Using existing version: {version}")

    # Set @prod alias
    time.sleep(1)
    result3, err3 = uc_api("registered-models/alias", "POST", {
        "name": uc_name,
        "alias": "prod",
        "version_num": int(version)
    })
    if err3:
        # Try different field name
        result3b, err3b = uc_api("registered-models/alias", "POST", {
            "name": uc_name,
            "alias": "prod",
            "version": version
        })
        if err3b:
            print(f"  Alias v1 error: {err3[:100]}")
            print(f"  Alias v2 error: {err3b[:100]}")
        else:
            print(f"  @prod set (v2) to version {version}")
    else:
        print(f"  @prod set to version {version}")

# Verify
print("\n=== Verification ===")
for model_name in MODELS:
    uc_name = f"{CATALOG}.ml.{model_name}"
    result4, err4 = uc_api(f"registered-models/alias?name={uc_name}&alias=prod")
    if err4:
        # Try GET with query string
        req = urllib.request.Request(
            f"{WORKSPACE}/api/2.0/mlflow/unity-catalog/registered-models/alias?name={uc_name.replace('.','%2E')}&alias=prod",
            headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req) as r:
                v = json.loads(r.read()).get("model_version", {}).get("version", "?")
                print(f"  {model_name} @prod = version {v}")
        except Exception as e2:
            print(f"  {model_name}: {err4[:100]}")
    else:
        v = result4.get("model_version", {}).get("version", "?")
        print(f"  {model_name} @prod = version {v}")
