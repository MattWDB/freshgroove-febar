# Architecture — System Context

These diagrams are first-class, versioned artifacts kept in sync with what is actually built. Written in Mermaid — text-diffable and rendered natively by GitHub.

**Sync rule:** Update the affected diagram in the same commit as the build change. A node must not appear unless it maps to a real, deployed resource. Designed-but-not-yet-built items are drawn dashed and labeled as gaps.

## Context Diagram (last updated: Session 1 — stub, no components deployed yet)

```mermaid
graph TD
    ERP["ERP / Warehouse System<br/>store_inventory.csv<br/>12 stores, 45 SKUs, 365 days"] --> V
    TMS["POS / Sales System<br/>sales_transactions.json<br/>Daily units sold by store + SKU"] --> V
    WX["External Events<br/>weather_disruptions.json<br/>Supply disruption events"] --> V
    PDF["Supplier Documents<br/>supplier_asn_pdfs/<br/>120 ASN shipping manifests"] --> V

    V["Databricks Volume<br/>freshgroove_febar.bronze.raw_landing<br/>PLANNED — not yet created"] --> LF

    LF["Lakeflow DLT Pipeline<br/>freshgroove-pipeline<br/>Bronze / Silver / Gold<br/>PLANNED — not yet created"] --> UC

    UC["Unity Catalog<br/>freshgroove_febar<br/>PLANNED — not yet created"] --> ML
    UC --> LB
    UC --> GA

    ML["ML Models × 3<br/>waste_classifier, demand_forecast, supplier_reliability<br/>PLANNED"] --> APP
    LB["Lakebase<br/>freshgroove schema<br/>PLANNED"] --> APP
    GA["Genie Agent<br/>FreshGroove Perishable Ops Intelligence<br/>PLANNED"] --> APP

    APP["FreshGroove App<br/>AppKit React/Node.js<br/>PLANNED"]
    APP --> DASH["AI/BI Dashboard<br/>Waste Risk Control Tower<br/>PLANNED"]

    PLANNER["Store Planner / Category Manager"] --> APP
```

Update this diagram after each build phase — replace PLANNED with the actual resource ID.
