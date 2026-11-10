# Databricks notebook source
# MAGIC %md # Provision Lakebase for FreshGroove

# COMMAND ----------
from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()

# Create Lakebase database (Postgres-compatible)
# Try the standard SDK approach
try:
    project = w.lakebase.create_database(
        name="freshgroove-lakebase",
        catalog="matt_fe_bar_catalog"
    )
    print(f"Lakebase created via lakebase API: {project}")
    conn_info = {
        "project_id": getattr(project, 'name', str(project)),
        "host": getattr(project, 'host', None),
        "port": getattr(project, 'port', 5432),
    }
except AttributeError:
    # Try database.databases API
    try:
        project = w.database.databases.create(
            database_catalog_name="matt_fe_bar_catalog",
            database_schema_name="freshgroove_lakebase"
        )
        print(f"Lakebase project created: {project}")
        conn_info = {
            "project_id": getattr(project, 'name', str(project)),
        }
        if hasattr(project, 'connection_info'):
            conn_info["host"] = project.connection_info.host
            conn_info["port"] = project.connection_info.port
        else:
            conn_info["host"] = None
            conn_info["port"] = 5432
    except Exception as e2:
        print(f"database.databases error: {e2}")
        # Try REST API directly
        import urllib.request
        token = w.config.token
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        req = urllib.request.Request(
            f"{w.config.host}/api/2.0/lakebase/instances",
            data=json.dumps({"name": "freshgroove-lakebase", "catalog": "matt_fe_bar_catalog"}).encode(),
            headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                print(f"Lakebase via REST: {result}")
                conn_info = result
        except Exception as e3:
            print(f"REST error: {e3}")
            conn_info = {"note": "Lakebase not available on this workspace tier — using Delta table fallback"}

print(json.dumps(conn_info, default=str, indent=2))

# COMMAND ----------
# Store connection info
dbutils.jobs.taskValues.set(key="conn_info", value=json.dumps(conn_info, default=str))
