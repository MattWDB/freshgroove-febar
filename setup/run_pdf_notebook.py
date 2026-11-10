#!/usr/bin/env python3
"""Runs the PDF generator notebook. Stdlib only."""
import json, urllib.request, subprocess, sys
sys.path.insert(0, "/Users/matthew.walding/freshgroove-febar")
from setup.token_helper import get_token

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"

token = get_token(PROFILE)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

serverless_config = {
    "run_name": "generate_pdfs_serverless",
    "tasks": [{
        "task_key": "generate_pdfs",
        "notebook_task": {
            "notebook_path": "/Workspace/Users/matthew.walding@databricks.com/freshgroove-febar/data_generation/generate_pdfs_notebook"
        },
        "environment_key": "default"
    }],
    "environments": [{"environment_key": "default", "spec": {"client": "2"}}]
}

req = urllib.request.Request(
    f"{WORKSPACE}/api/2.1/jobs/runs/submit",
    data=json.dumps(serverless_config).encode(),
    headers=headers, method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        run_id = result.get("run_id")
        print(f"Notebook run submitted: run_id={run_id}")
        print(f"Monitor at: {WORKSPACE}/jobs/runs/{run_id}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error: {body}")
    sys.exit(1)
