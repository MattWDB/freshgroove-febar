# FreshGroove FE Bar — Build Journal

One entry per session. Format: Session N — DATE — Topic.
Newest entries at the bottom.

---

## Session 1 — 2026-11-10 — Project Setup & Scenario Design

**What:** Created project directory ~/freshgroove-febar. Databricks CLI profile fe-bar already configured for fevm-matt-fe-bar workspace (org 7474655831226413). Initialized GitHub repo MattWDB/freshgroove-febar (public). Wrote foundational documentation: decisions log, value model, architecture context diagram.

**Why:** FE Bar rubric rewards documented decision-making from the start. A decisions file written before any code is written is more credible than one written at submission time. Build journal captures the session-by-session story the evaluator needs to understand the journey.

**Outcome:** Project scaffold committed and pushed. Workspace connection verified. GitHub repo public and readable at https://github.com/MattWDB/freshgroove-febar.

**Key decision:** FreshGroove Foods (CPG perishable waste + OTIF) chosen over NorthPeak Retail (store ops) and a supply-chain OTIF scenario because: (a) perishable waste is a specific, quantifiable problem distinct from the reference builds, (b) the $3.5M/yr figure is grounded in the synthetic data we will generate, and (c) prior FreshFlow build validates the ML signal in this domain.

**Evidence:** docs/evidence/phase0_setup_validation.txt

---

## Session 2 — 2026-11-10 — Synthetic Data Generation

**What:** Generated 201,480 rows of store inventory and sales transactions across 12 stores, 45 SKUs, 365 days. Generated 25 weather/disruption events. Wrote PDF generator notebook (120 ASN PDFs, to run on Databricks). Uploaded all files to Databricks Volume at matt_fe_bar_catalog.bronze.raw_landing. Created schemas: bronze, silver, gold, ml.

**Why:** FE Bar requires 100% synthetic data for a reproducible, signal-rich dataset. Intentionally injected correlated patterns (strawberry April spike, rising supplier late rates, warehouse temp failures, lane-based spoilage) so the ML models have genuine signal to learn — not just noise.

**Key decision:** Using `matt_fe_bar_catalog` instead of `freshgroove_febar` — the workspace does not grant CREATE CATALOG on the metastore. matt_fe_bar_catalog is the pre-provisioned workspace catalog with identical schema structure. All architecture references updated accordingly.

**Data signals confirmed:**
- Strawberry April spike (NE, >20% spoilage): 73 rows ✓
- Supplier late rate trend: SUP-0001 rising 22.7% → 24.1% ✓
- Warehouse temp failures: 3 dates (2025-07-12, 2025-10-12, 2025-10-24) ✓
- Lane spoilage: ocean=14% > rail=12% > truck=10% ✓

**Evidence:** docs/evidence/phase1_data_validation.txt
