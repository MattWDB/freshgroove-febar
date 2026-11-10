#!/usr/bin/env python3
"""Runs a Databricks notebook synchronously and returns output. Stdlib only."""
import json, urllib.request, subprocess, time, sys
sys.path.insert(0, "/Users/matthew.walding/freshgroove-febar")
from setup.token_helper import get_token

PROFILE   = "fe-bar"
WORKSPACE = "https://fevm-matt-fe-bar.cloud.databricks.com"

notebook_path = sys.argv[1] if len(sys.argv) > 1 else ""
timeout_min   = int(sys.argv[2]) if len(sys.argv) > 2 else 15
if not notebook_path:
    print("Usage: python3 setup/run_notebook.py /Workspace/path/to/notebook [timeout_minutes]")
    sys.exit(1)

token = get_token(PROFILE)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

run_config = {
    "run_name": f"fe-bar-run-{notebook_path.split('/')[-1]}",
    "tasks": [{
        "task_key": "run_notebook",
        "notebook_task": {"notebook_path": notebook_path},
        "environment_key": "default"
    }],
    "environments": [{"environment_key": "default", "spec": {"client": "2"}}]
}

req = urllib.request.Request(
    f"{WORKSPACE}/api/2.1/jobs/runs/submit",
    data=json.dumps(run_config).encode(),
    headers=headers, method="POST"
)
with urllib.request.urlopen(req) as resp:
    run_id = json.loads(resp.read()).get("run_id")
    print(f"Run submitted: run_id={run_id}")
    print(f"Monitor: {WORKSPACE}/jobs/runs/{run_id}")

max_polls = timeout_min * 6  # poll every 10s
print(f"Polling for completion (timeout {timeout_min} min)...")
for i in range(max_polls):
    time.sleep(10)
    poll = urllib.request.Request(
        f"{WORKSPACE}/api/2.1/jobs/runs/get?run_id={run_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(poll) as r:
        status = json.loads(r.read())
    life         = status.get("state", {}).get("life_cycle_state", "")
    result_state = status.get("state", {}).get("result_state", "")
    if i % 3 == 0:
        print(f"  [{i*10}s] {life} / {result_state}")
    if life in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
        print(f"Run finished: {result_state}")
        if result_state == "SUCCESS":
            try:
                out_req = urllib.request.Request(
                    f"{WORKSPACE}/api/2.1/jobs/runs/get-output?run_id={run_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                with urllib.request.urlopen(out_req) as out_resp:
                    out = json.loads(out_resp.read())
                    nb_out = out.get("notebook_output", {})
                    print("--- NOTEBOOK OUTPUT ---")
                    print(nb_out.get("result", "(no result cell)")[:3000])
            except Exception as e:
                print(f"Could not fetch output: {e}")
        else:
            # Print error
            tasks = status.get("tasks", [{}])
            if tasks:
                state = tasks[0].get("state", {})
                print(f"Error: {state.get('state_message', 'unknown error')}")
        sys.exit(0 if result_state == "SUCCESS" else 1)

print("Timeout — check run manually in workspace UI")
sys.exit(1)
