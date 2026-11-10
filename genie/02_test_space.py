#!/usr/bin/env python3
"""Tests the Genie space / AI Assistant with 3 sample questions using databricks CLI.
Run: python genie/02_test_space.py
"""
import subprocess, json, sys

PROFILE = "fe-bar"
WAREHOUSE_ID = "13d586337d2fb9b5"

test_questions = [
    "Which SKUs are at highest risk in matt_fe_bar_catalog gold schema?",
    "What is our current waste rate from matt_fe_bar_catalog gold schema?",
    "Which suppliers have the highest late rate in matt_fe_bar_catalog gold schema?",
]

for q in test_questions:
    print(f"\nQ: {q}")
    result = subprocess.run([
        "databricks", "genie", "ask", q,
        "--warehouse-id", WAREHOUSE_ID,
        "--profile", PROFILE,
        "--output", "json"
    ], capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        print(f"Status: {data.get('status')}")
        text = data.get('text', '')
        print(f"Answer: {text[:500]}")
        for tc in data.get('tool_calls', []):
            if tc.get('sql'):
                print(f"SQL: {tc['sql'][:200]}")
                break
    else:
        print(f"Error: {result.stderr[:200]}")
