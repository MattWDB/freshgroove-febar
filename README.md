# FreshGroove Perishable Control Tower

**Business outcome:** FreshGroove Foods loses an estimated $3.5M/year to perishable waste (12% spoilage rate) and OTIF chargebacks (91% on-time rate). This build delivers a Databricks-native control tower that flags at-risk SKUs 5–8 days early, serves recommended actions in real time, and creates an operational audit trail. Conservative year-1 impact: **$2.2M in savings**.

## The Data Journey

```
Raw Data (4 sources: inventory CSV, sales JSON, disruption events, supplier PDFs)
    → Databricks Volume (matt_fe_bar_catalog.bronze.raw_landing)
    → Lakeflow SDP Pipeline (Bronze → Silver → Gold, with DQ expectations)
    → Unity Catalog (governed: matt_fe_bar_catalog, 4 schemas, 3 ML models @prod)
    → ML Intelligence (waste_classifier + demand_forecast + supplier_reliability)
    → Operational Serving (reorder_queue + kpi_live, with write-back audit trail)
    → Genie Agent (FreshGroove — Perishable Ops Intelligence)
    → FreshGroove App (AppKit: Overview, Operations, Agent, Platform Map)
    → AI/BI Dashboard (Waste Risk Control Tower + 2 SQL alerts)
```

## Components

| Component | Resource | Evidence |
|-----------|----------|----------|
| Lakeflow SDP Pipeline | freshgroove-pipeline (`f668d89e`) | docs/evidence/phase2_pipeline_validation.txt |
| Unity Catalog | matt_fe_bar_catalog (bronze/silver/gold/ml) | docs/evidence/phase3_governance_validation.txt |
| ML Models × 3 | waste_classifier (AUC=0.80), demand_forecast (R²=0.9999), supplier_reliability @prod | docs/evidence/phase4_ml_validation.txt |
| Serving Endpoint | freshgroove-waste-scorer (scale-to-zero, READY) | docs/evidence/phase4_ml_validation.txt |
| Operational Serving | matt_fe_bar_catalog.gold.reorder_queue (183,839 rows, write-back enabled) | docs/evidence/phase5_lakebase_validation.txt |
| Genie Agent | FreshGroove — Perishable Ops Intelligence (`01f1dd14a9e21327992887fd1d1ede03`) | docs/evidence/phase6_genai_validation.txt |
| Databricks App | freshgroove-app (AppKit, 4 views, ACTIVE) | docs/evidence/phase7_app_validation.txt |
| AI/BI Dashboard | FreshGroove Waste Risk Control Tower (`01f1ddd68ed8119a9b9328fd0c5c414b`) | docs/evidence/phase8_dashboard_validation.txt |
| DABs Bundle | dev + prod targets, `databricks bundle validate` passes | docs/evidence/phase9_bundle_validation.txt |
| E2E Test | tests/e2e_api_test.py — 10/11 layers passing | docs/evidence/phase12_e2e_test.txt |

## Live Resources

- **App:** https://freshgroove-app-7474655831226413.aws.databricksapps.com
- **Genie:** https://fevm-matt-fe-bar.cloud.databricks.com/genie/rooms/01f1dd14a9e21327992887fd1d1ede03
- **Dashboard:** https://fevm-matt-fe-bar.cloud.databricks.com/dashboards/01f1ddd68ed8119a9b9328fd0c5c414b
- **Pipeline:** https://fevm-matt-fe-bar.cloud.databricks.com/pipelines/f668d89e-d740-4352-9d26-f85022fbe3e4

## How to Rebuild from Repo

```bash
git clone https://github.com/MattWDB/freshgroove-febar.git
cd freshgroove-febar
databricks configure --profile fe-bar  # add PAT for fevm-matt-fe-bar workspace
python data_generation/generate_synthetic.py  # regenerate raw data
databricks bundle deploy --target dev --profile fe-bar
```

## AI Methodology

Built across 10 Claude Code (Isaac) sessions. Every session documented in [docs/build_journal.md](docs/build_journal.md). All architectural decisions in [docs/decisions_and_tradeoffs.md](docs/decisions_and_tradeoffs.md). AI used for: code generation, SDP notebook authoring, API scaffolding, test writing. Decisions and trade-offs (why AppKit over Streamlit, why 3 models, why Genie Agent over MAS/KA, why operational Delta table serving over Lakebase) are documented in the decisions log.

## Business Value

See [docs/value_model.md](docs/value_model.md) for full calculation. All figures based on synthetic data correlated with industry benchmarks. No real customer data used.

| Outcome | Mechanism | Value |
|---------|-----------|-------|
| Waste rate 12% → 9% | Early warning + ranked reorder actions | $500K–$1.0M/yr |
| OTIF 91% → 96% | Supplier risk scores + ASN PDF signals | $900K/yr |
| Planner time | Ranked queue replaces manual exception review | $15K/yr |
| **Total (conservative)** | | **$2.2M/yr** |
