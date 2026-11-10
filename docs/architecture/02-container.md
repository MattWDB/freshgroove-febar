# Container Diagram (last updated: Session 3 — Pipeline deployed and running)

```mermaid
graph TD
    V["Databricks Volume<br/>matt_fe_bar_catalog.bronze.raw_landing<br/>store_inventory.csv · sales_transactions.ndjson<br/>weather_disruptions.ndjson · supplier_asn_pdfs/"] --> P

    P["Lakeflow SDP Pipeline<br/>freshgroove-pipeline<br/>ID: f668d89e-d740-4352-9d26-f85022fbe3e4<br/>catalog: matt_fe_bar_catalog"] --> B

    B["Bronze Layer<br/>matt_fe_bar_catalog.bronze.*<br/>bronze_inventory_raw (201,480 rows)<br/>bronze_sales_raw (201,480 rows)<br/>bronze_disruptions_raw (25 rows)"] --> S

    S["Silver Layer<br/>matt_fe_bar_catalog.silver.*<br/>silver_inventory · silver_sales<br/>silver_inventory_sales (201,480 rows) · silver_disruptions<br/>DQ expectations: valid_spoilage_units, valid_date, valid_units"] --> G

    G["Gold Layer<br/>matt_fe_bar_catalog.gold.*<br/>gold_waste_risk_features (201,480 rows)<br/>gold_kpi_summary (1 row) · gold_supplier_risk (7 rows)"] --> UC

    UC["Unity Catalog<br/>matt_fe_bar_catalog<br/>Table comments on all gold tables ✅<br/>ML model registry: .ml schema (pending Session 4)"] --> ML
    UC --> LB
    UC --> GA

    ML["ML Models × 3<br/>waste_classifier + demand_forecast + supplier_reliability<br/>PLANNED — Session 4"] --> APP
    LB["Lakebase Postgres<br/>reorder_queue + kpi_summary<br/>PLANNED — Session 5"] --> APP
    GA["Genie Agent<br/>FreshGroove Perishable Ops Intelligence<br/>PLANNED — Session 6"] --> APP

    APP["FreshGroove App<br/>AppKit React/Node.js<br/>PLANNED — Session 7"]
```

## Deployed Resources

| Resource | ID/Path | Status |
|----------|---------|--------|
| Volume | matt_fe_bar_catalog.bronze.raw_landing | ✅ Live (3 dirs, 3 files) |
| Pipeline | freshgroove-pipeline — `f668d89e-d740-4352-9d26-f85022fbe3e4` | ✅ IDLE/COMPLETED |
| Bronze tables | matt_fe_bar_catalog.bronze.bronze_* (3 tables) | ✅ 201,480 rows |
| Silver tables | matt_fe_bar_catalog.silver.silver_* (4 tables) | ✅ 201,480 rows |
| Gold tables | matt_fe_bar_catalog.gold.gold_* (3 tables) | ✅ Populated |
| UC governance | Table comments on all 3 gold tables | ✅ Applied |

## DQ Expectations (active in silver layer)

- `silver_inventory`: `expect_or_drop("valid_spoilage_units", "spoilage_units >= 0 AND spoilage_units <= on_hand_units")`
- `silver_inventory`: `expect_or_drop("valid_date", "date IS NOT NULL")`
- `silver_inventory`: `expect("store_exists", "store_id IS NOT NULL")`
- `silver_sales`: `expect_or_drop("valid_units", "units_sold >= 0")`
- `silver_sales`: `expect_or_drop("valid_date_sales", "date IS NOT NULL")`
