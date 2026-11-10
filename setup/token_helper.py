"""
Shared token helper for all setup scripts.
Usage: from setup.token_helper import get_token
Or:    TOKEN = get_token("fe-bar")
"""
import json, subprocess

def get_token(profile="fe-bar"):
    """Get Databricks OAuth token. The CLI returns JSON since ~0.230."""
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile],
        capture_output=True, text=True
    )
    raw = result.stdout.strip()
    try:
        data = json.loads(raw)
        return data.get("access_token", raw)
    except (json.JSONDecodeError, ValueError):
        return raw
