# Decisions & Trade-offs

Why the solution is built the way it is. A short, honest "why this and not that."

| Decision | Why | Trade-off / What we gave up |
|---|---|---|
| Perishable waste + OTIF as the hero story | Specific, quantifiable, CPG-real. Grocery waste (12% → 6%) + chargeback reduction connects directly to a VP's P&L. | Narrower than "supply chain analytics" — deliberately so. Generic builds score low. |
| 3 ML models (waste_classifier + demand_forecast + supplier_reliability) | Rubric targets Exceeds on Build + AI Mindset. Three models demonstrate breadth; each answers a distinct business question. | Two intelligence stacks to maintain; mitigated by using HistGradientBoosting across all three with a shared feature pipeline. |
| Genie Agent over MAS / Knowledge Assistant | MAS and KA are Legacy (Sept 2026) / EoS H1 2027. Genie Agent is GA, go-forward. A curated Genie Agent covers both GenAI explainability and NL query. | No multi-agent orchestration (not needed here). |
| AppKit (React + TypeScript + Express) over Streamlit | Production-quality exec demo. AppKit's native plugins (lakebase, genie, serving) wrap our exact integrations. Exec sees a real product, not a notebook UI. | More code than Streamlit. Mitigated by adapting the NorthPeak reference implementation (my own prior work). |
| Lakebase with OLTP write-back (not analytics-only) | Demonstrates operational serving — planners acknowledge risks, creating an audit trail. Evaluator distinguishes reporting tools from operational ones. | Requires Postgres provisioning and SP grants. |
| freshgroove_febar catalog (own catalog, not shared) | Hold ALL_PRIVILEGES; schemas + volumes are DAB-native. Avoids metastore CREATE CATALOG admin dependency. | A personal build catalog — acceptable for a demo build. |
| 100% synthetic data | Rubric requirement (no real customer data). Full control of disruption patterns — inject the strawberry seasonal spike and supplier failures so the ML model has a genuine signal to learn. | Must inject realistic correlated patterns or the model learns nothing. |
| Mermaid living diagrams in-repo | Text-diffable, GitHub-native, kept in sync with what is actually deployed. Evaluator can read them as text. | Less visually polished than Lucidchart or draw.io; deck redraws the flow in HTML/CSS. |
