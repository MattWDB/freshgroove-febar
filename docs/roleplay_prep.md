# Roleplay Prep — FreshGroove Perishable Control Tower

## Pre-Call Checklist (15 minutes before Yoodli)

- [ ] Authenticate: `databricks auth login --host https://fevm-matt-fe-bar.cloud.databricks.com --profile fe-bar`
- [ ] Wake the ML endpoint (scale-to-zero takes ~60s): send a test curl to freshgroove-waste-scorer
- [ ] Open app in browser: https://freshgroove-app-7474655831226413.aws.databricksapps.com
- [ ] Verify Overview loads with real KPI numbers (not zeros)
- [ ] Send one warm-up question to Genie: "What is our current waste rate?"
- [ ] Open AI/BI dashboard — confirm charts render
- [ ] Open deck/index.html in a browser tab (visual companion during demo)

## Demo Structure (Tell → Show → Tell)

**Total time: 20–25 minutes**

### Part 1 — Tell: The Business Problem (2 min, no app yet)

"I want to set the stage before I show you anything. FreshGroove Foods has two problems that together cost about $3.5 million a year.

The first is perishable waste. Right now, about 12% of perishable inventory — produce, dairy, bakery — expires unsold. The industry benchmark is 6%. That gap costs $2 million a year in destroyed product.

The second is OTIF chargebacks. When a delivery arrives late or short, the retailer deducts 3% of the invoice. FreshGroove's current OTIF rate is 91% — the retailer threshold is 98%. That's $1.5 million a year in penalties.

The root cause of both is the same: planners find out about problems after they happen. The dairy run was over-ordered and you find out when the markdown hits. The strawberry delivery was short and you find out when the truck doesn't show. No early warning, no recommended action, no audit trail.

What I built is a system that flips that. Let me show you what it looks like when it works."

(Now open the app.)

### Part 2 — Show: The Outcome (6–8 min)

**Stop 1 — Overview (1–2 min):**
"This is what a planner sees every morning. Four numbers: current waste rate 11.9%, spoilage cost annualized, OTIF rate 91%, chargeback cost $1.5M. These are pulled from this morning's pipeline run — not yesterday's report."

**Stop 2 — Operations Queue (2–3 min):**
"This is the reorder queue — a ranked list of every SKU at elevated waste risk this week, ordered by probability score. Click into the top item: SKU-STRWBRY at Northeast stores. 78% probability of excess waste. The recommended action is already written: reduce order by 120 units, check backup supplier SUP-0007. The planner clicks Acknowledge — that write goes to the database with their name and timestamp. That's the audit trail. If a retailer deduction comes in next week, the VP can show: we knew about the risk on Monday and acted on it the same day."

(Pause. Ask: "Does that match the kind of exception review your planners do today?")

**Stop 3 — Ask the Agent (2 min):**
"Now the planner has a question that isn't on this screen — which suppliers are driving the most risk this month. They just ask. (Type: 'Which suppliers have the highest waste risk contribution this month?') The agent writes the SQL, runs it against governed data, and returns the ranked list. The SQL is shown — not a black box."

### Part 3 — Tell: Land the Value (1 min)

"Instead of a Monday post-mortem about last week's spoilage, your planners have this list on Monday morning with 8 days of lead time. The action is already written. 30 seconds to acknowledge. The VP has a timestamped audit trail. We've modeled this at $2.2M in year-one savings: $500K–$1M from cutting waste from 12% to 9%, and $900K from improving OTIF from 91% to 96%."

(Pause for business stakeholder questions before architecture.)

### Part 4 — Show: Architecture (3–4 min, for technical persona)

"Let me show you how this is actually built. (Navigate to Platform Map.) Every tile with a glowing dot is live in this workspace right now — not a diagram. Watch. (Click Lakeflow tile.) That opens the actual pipeline. (Click the catalog tile.) That's Unity Catalog — every table and model governed here.

Data journey left to right: four sources feed in — store inventory as CSV, POS sales as JSON, disruption events, and supplier shipping documents as PDFs. All land in a Databricks Volume.

Lakeflow processes in three passes: Bronze reads raw files into Delta tables — no transformation, full audit trail. Silver cleans, joins, and enforces quality rules. Gold creates the ML feature tables. Everything in Unity Catalog with column descriptions that make Genie accurate.

Three ML models score every SKU daily: waste classifier, demand forecast, supplier reliability. All registered in Unity Catalog with @prod alias — the app always calls @prod, so we can retrain and promote a new version without touching app code.

The app reads from an operational Delta table — fast enough for the UI, with write-back via Delta CDF. The Genie Agent answers natural language queries against governed Gold tables."

### Part 5 — Tell: Connect to Value (1 min)

"The reason this architecture matters: every layer is auditable. You can trace a risk score back to the raw supplier file. You can see when the model was last trained and what its accuracy was. You can see who acknowledged which risk and when. That's what the VP needs for a chargeback dispute, and what the CFO needs for the board deck."

## Objection Handling

**"How do we know these recommendations are accurate?"**
"The waste classifier was trained on 12 months of historical data — it's seen the April strawberry pattern before. It hit 80% AUC in validation. Start with HIGH-risk items only, which have the clearest signal. In the first 30 days, tell us which recommendations were wrong — that's the retraining loop."

**"My planners won't change their workflow."**
"It's built to meet them where they are. The reorder queue looks like a spreadsheet. The recommended action is already written — two taps to acknowledge. In similar deployments, adoption is fastest when planners realize they look good in Monday stand-ups because the risk was on the list and actioned before anything went wrong."

**"How fresh is the data?"**
"The Lakeflow pipeline runs at 6am daily. By 8am, planners have last night's data. For daily replenishment planning, that's sufficient. A streaming path is the next architectural step for intraday alerting."

**"What happens when the model is wrong?"**
"The model gives a probability — 78% means 'this warrants attention today.' The planner makes the final call. We also have Lakehouse Monitoring tracking feature drift daily, and the @challenger alias pattern in Unity Catalog means a retrained model is always being validated before it replaces @prod."

**"Why SDP / Lakeflow instead of standard notebooks?"**
"Two reasons. First, declarative: you define what each table should look like and what quality rules apply — the engine handles execution order and retries. Second, DQ expectations are first-class: quarantined rows are tracked, not silently dropped. For a perishable use case where a bad spoilage rate could trigger a wrong recommendation, that's the right trade-off."

**"Who maintains this after you leave?"**
"The full stack is defined in databricks.yml — two commands rebuild everything from the repo. The architecture diagrams in docs/architecture/ are Mermaid files kept in sync with what's deployed. The most ongoing maintenance is model retraining, which is a scheduled notebook run that a junior data engineer can own."

**"How does this scale to all 1,200 stores?"**
"The architecture already handles it — the pipeline and model batch-score every store × SKU combination daily. Adding stores means adding rows to the inventory CSV, not changing any code. I'd recommend a phased approach: start with a POC on your 50 highest-volume stores, validate model accuracy and planner adoption over 4–6 weeks, then work with your AE on an SOW for the full rollout."

## Terminology to Correct (if AI persona uses old terms)

- **"DLT"** → "That's now called Spark Declarative Pipelines, or SDP — same technology, same Python API, just renamed as part of the Lakeflow branding."
- **"MAS" or "Knowledge Assistant"** → "Those are legacy as of September 2026, end-of-service H1 2027. The Genie Agent is the go-forward product, which is what we built."

## Key Numbers to Have Ready

| Metric | Value |
|--------|-------|
| Waste rate (current) | 11.9% |
| OTIF rate (current) | 91% |
| Annual waste cost | ~$2M (at 12% × $45/unit) |
| Annual chargebacks | ~$1.5M |
| Total addressable | $3.5M/yr |
| Conservative year-1 savings | $2.2M/yr |
| waste_classifier AUC | 0.80 |
| Rows scored daily | 201,480 |
| HIGH risk SKUs (last 7 days) | 663 |
| Reorder queue size | 183,839 rows |
| Build sessions | 10 |
| Evidence files | 11 |
