#!/usr/bin/env python3
"""
FreshGroove FE Bar — Synthetic Data Generator
Stdlib only: csv, json, random, datetime, math
Run: python data_generation/generate_synthetic.py
Outputs: data_generation/raw/store_inventory.csv, sales_transactions.json, weather_disruptions.json
NOTE: Catalog used is matt_fe_bar_catalog (freshgroove_febar name requires CREATE CATALOG privilege)
"""
import csv, json, random, math, os
from datetime import date, timedelta

random.seed(42)

# Config
START = date(2025, 4, 1)
END   = date(2026, 3, 31)
DATES = [START + timedelta(d) for d in range((END - START).days + 1)]

STORES = {
    "STR-001": "Northeast", "STR-002": "Northeast",
    "STR-003": "Northeast", "STR-004": "Northeast",
    "STR-005": "Southeast", "STR-006": "Southeast", "STR-007": "Southeast",
    "STR-008": "Midwest",   "STR-009": "Midwest",   "STR-010": "Midwest",
    "STR-011": "West",      "STR-012": "West",
}

SUPPLIERS = {
    "SUP-0001": {"lane": "truck", "base_late": 0.15},  # unreliable, rising
    "SUP-0002": {"lane": "rail",  "base_late": 0.18},  # unreliable, rising
    "SUP-0003": {"lane": "ocean", "base_late": 0.20},  # unreliable, rising
    "SUP-0004": {"lane": "truck", "base_late": 0.05},
    "SUP-0005": {"lane": "rail",  "base_late": 0.04},
    "SUP-0006": {"lane": "ocean", "base_late": 0.08},
    "SUP-0007": {"lane": "truck", "base_late": 0.03},
}

LANE_SPOILAGE = {"ocean": 0.14, "rail": 0.12, "truck": 0.10}

SKU_CATEGORIES = {}
skus = []
for i in range(1, 16):
    sid = f"SKU-PROD{i:02d}"
    SKU_CATEGORIES[sid] = "produce"
    skus.append(sid)
for i in range(1, 13):
    sid = f"SKU-DAIRY{i:02d}"
    SKU_CATEGORIES[sid] = "dairy"
    skus.append(sid)
for i in range(1, 11):
    sid = f"SKU-BAKE{i:02d}"
    SKU_CATEGORIES[sid] = "bakery"
    skus.append(sid)
for i in range(1, 9):
    sid = f"SKU-PREP{i:02d}"
    SKU_CATEGORIES[sid] = "prepared_foods"
    skus.append(sid)
# Special strawberry SKU
SKU_CATEGORIES["SKU-STRWBRY"] = "produce"
skus.append("SKU-STRWBRY")

SKU_NAMES = {s: s.replace("SKU-", "").replace("-", " ").title() + " Fresh" for s in skus}
SKU_NAMES["SKU-STRWBRY"] = "Strawberries 1lb"

# Assign each SKU a primary supplier
SKU_SUPPLIER = {}
sup_list = list(SUPPLIERS.keys())
for i, s in enumerate(skus):
    SKU_SUPPLIER[s] = sup_list[i % len(sup_list)]
SKU_SUPPLIER["SKU-STRWBRY"] = "SUP-0001"  # chronically unreliable supplier

# Warehouse temperature failure events (3 random dates)
random.seed(99)
temp_fail_dates = set()
while len(temp_fail_dates) < 3:
    d = random.choice(DATES)
    temp_fail_dates.add(d)
temp_fail_dates = sorted(temp_fail_dates)
temp_fail_stores = {d: random.sample(list(STORES.keys()), 3) for d in temp_fail_dates}

os.makedirs("data_generation/raw", exist_ok=True)

# ── Inventory ──────────────────────────────────────────────────────────────
inventory_rows = []
sales_rows = []

random.seed(42)  # re-seed for reproducibility
for dt in DATES:
    year_frac = (dt - date(2025, 1, 1)).days / 365.0
    for store_id, region in STORES.items():
        for sku_id in skus:
            cat = SKU_CATEGORIES[sku_id]
            sup_id = SKU_SUPPLIER[sku_id]
            lane = SUPPLIERS[sup_id]["lane"]
            base_spoilage = LANE_SPOILAGE[lane]

            # Seasonal demand
            if cat == "bakery" and dt.month in (11, 12):
                demand_mult = 1.35
            elif cat in ("produce", "prepared_foods") and 4 <= dt.month <= 6:
                demand_mult = 1.20
            else:
                demand_mult = 1.0

            # Strawberry April spike at Northeast
            is_strawberry_window = (sku_id == "SKU-STRWBRY" and
                                    region == "Northeast" and
                                    dt.month == 4)
            if is_strawberry_window:
                demand_mult = 1.40

            # Supplier unreliability (rising over time)
            base_late = SUPPLIERS[sup_id]["base_late"]
            if sup_id in ("SUP-0001", "SUP-0002", "SUP-0003"):
                late_rate = base_late + 0.03 * year_frac
            else:
                late_rate = base_late

            # Strawberry supplier shortage in April
            if is_strawberry_window and random.random() < 0.65:
                recv_pct = random.uniform(0.55, 0.80)
            elif random.random() < late_rate:
                recv_pct = random.uniform(0.70, 0.95)
            else:
                recv_pct = random.uniform(0.95, 1.0)

            units_ordered = int(random.randint(80, 200) * demand_mult)
            units_received = int(units_ordered * recv_pct)
            on_hand = units_received + random.randint(0, 20)

            # Spoilage
            spoilage_rate = base_spoilage * random.uniform(0.7, 1.4)

            # Warehouse temp failure → 3× dairy spoilage
            warehouse_temp_ok = True
            if dt in temp_fail_dates and store_id in temp_fail_stores[dt]:
                warehouse_temp_ok = False
                if cat == "dairy":
                    spoilage_rate = min(spoilage_rate * 3.0, 0.45)

            # Strawberry waste spike
            if is_strawberry_window and recv_pct < 0.85:
                spoilage_rate = min(spoilage_rate * 2.5, 0.50)

            spoilage_units = int(on_hand * spoilage_rate)
            spoilage_units = min(spoilage_units, on_hand)

            inventory_rows.append({
                "date": dt.isoformat(),
                "store_id": store_id,
                "sku_id": sku_id,
                "sku_name": SKU_NAMES[sku_id],
                "category": cat,
                "on_hand_units": on_hand,
                "units_ordered": units_ordered,
                "units_received": units_received,
                "spoilage_units": spoilage_units,
                "supplier_id": sup_id,
                "region": region,
                "warehouse_temp_ok": str(warehouse_temp_ok).lower(),
            })

            # Sales
            units_sold = max(0, int((on_hand - spoilage_units) * random.uniform(0.70, 0.98)))
            sales_rows.append({
                "date": dt.isoformat(),
                "store_id": store_id,
                "sku_id": sku_id,
                "units_sold": units_sold,
                "unit_price": round(random.uniform(2.5, 8.5), 2),
            })

# Write inventory CSV
inv_fields = ["date","store_id","sku_id","sku_name","category","on_hand_units",
              "units_ordered","units_received","spoilage_units","supplier_id",
              "region","warehouse_temp_ok"]
with open("data_generation/raw/store_inventory.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=inv_fields)
    w.writeheader()
    w.writerows(inventory_rows)

# Write sales JSON
with open("data_generation/raw/sales_transactions.json", "w") as f:
    json.dump(sales_rows, f)

# ── Weather disruptions ───────────────────────────────────────────────────
disruption_descriptions = [
    ("weather_delay", "Northeast", "Severe winter storm caused 3-day road closures across the Northeast corridor, delaying fresh produce deliveries from regional DCs."),
    ("port_congestion", "West", "Port of Los Angeles container backlog extended lead times by 5-7 days for ocean freight, impacting West Coast perishable imports."),
    ("supplier_strike", "Midwest", "Warehouse workers' strike at a major Midwest distribution hub halted outbound shipments for 48 hours."),
    ("weather_delay", "Southeast", "Tropical storm warning closed Florida highways, disrupting last-mile delivery to Southeast grocery chains for 2 days."),
    ("temperature_event", "Northeast", "Refrigeration equipment failure at Northeast DC forced emergency product recall for dairy and prepared foods."),
    ("port_congestion", "West", "Customs inspection backlog at Seattle port delayed organic produce shipments by 4 days."),
    ("weather_delay", "Midwest", "Ice storm across the Midwest caused widespread carrier delays, with 60% of scheduled deliveries rescheduled."),
    ("supplier_strike", "Northeast", "SUP-0001 primary strawberry supplier work stoppage impacted April shipments — 65% of orders arrived short."),
    ("temperature_event", "Southeast", "Heatwave event raised ambient temperatures at unrefrigerated crossdock facilities, accelerating spoilage for bakery items."),
    ("weather_delay", "West", "Wildfire smoke advisory caused 1-day closure of West Coast agricultural transit routes."),
    ("port_congestion", "West", "Red Sea shipping disruption rerouted ocean freight around Cape of Good Hope, adding 14 days to West Coast delivery windows."),
    ("supplier_strike", "Midwest", "SUP-0002 rail carrier labor dispute reduced rail freight capacity by 40% for 1 week."),
    ("weather_delay", "Northeast", "Nor'easter blizzard shut down New England highway network for 36 hours, impacting all inbound perishable shipments."),
    ("temperature_event", "Midwest", "Prolonged cold snap disrupted greenhouse produce supply, causing shortages in leafy green SKUs."),
    ("weather_delay", "Southeast", "Hurricane season early arrival caused pre-emptive store closures in coastal Southeast markets."),
    ("port_congestion", "West", "Labor slowdown at Long Beach port increased container dwell time, raising risk for refrigerated ocean freight."),
    ("supplier_strike", "Northeast", "SUP-0001 and SUP-0003 simultaneous capacity constraints during peak strawberry season caused widespread Northeast stockouts."),
    ("weather_delay", "Midwest", "Tornado warnings caused temporary DC shutdowns across the Kansas City distribution hub."),
    ("temperature_event", "Northeast", "Unexpected warm spell in October caused accelerated ripening in apple and pear SKUs."),
    ("weather_delay", "West", "Pacific Coast atmospheric river event flooded key highway segments, delaying truck deliveries by 48 hours."),
    ("port_congestion", "West", "Port of Oakland labor dispute reduced throughput by 30% for 10 days during peak import season."),
    ("supplier_strike", "Southeast", "Agricultural worker shortage in Florida impacted fresh strawberry and citrus harvest volume."),
    ("weather_delay", "Northeast", "Late-season snowstorm disrupted April produce shipments just as seasonal demand spike began."),
    ("temperature_event", "Midwest", "Refrigerated trailer shortage during summer peak caused backlog of perishable goods at Midwest crossdocks."),
    ("weather_delay", "Southeast", "Gulf Coast fog advisory reduced truck transit speeds, adding 1 day to all Southeast delivery windows."),
]

events = []
used_dates = set()
random.seed(55)
for i, (etype, region, desc) in enumerate(disruption_descriptions):
    while True:
        d = random.choice(DATES)
        if d not in used_dates:
            used_dates.add(d)
            break
    severity = random.choice(["low", "medium", "high"])
    impact = round(random.uniform(0.05, 0.25), 2)
    events.append({
        "event_date": d.isoformat(),
        "event_type": etype,
        "region": region,
        "severity": severity,
        "supply_impact_pct": impact,
        "description": desc,
    })

events.sort(key=lambda x: x["event_date"])

with open("data_generation/raw/weather_disruptions.json", "w") as f:
    json.dump(events, f, indent=2)

# ── Summary stats ──────────────────────────────────────────────────────────
total_inv = len(inventory_rows)
total_sales = len(sales_rows)

spoilage_vals = [r["spoilage_units"] / max(r["on_hand_units"], 1) for r in inventory_rows]
mean_sp = sum(spoilage_vals) / len(spoilage_vals)
max_sp  = max(spoilage_vals)

by_region = {}
for r in inventory_rows:
    by_region.setdefault(r["region"], []).append(
        r["spoilage_units"] / max(r["on_hand_units"], 1))
region_means = {k: sum(v)/len(v) for k, v in by_region.items()}

# Strawberry April spike check
strwbry_ne_april = [r for r in inventory_rows
                    if r["sku_id"] == "SKU-STRWBRY"
                    and r["region"] == "Northeast"
                    and r["date"].startswith("2025-04")
                    and r["spoilage_units"] / max(r["on_hand_units"], 1) > 0.20]

# Supplier late rate trend
sup_by_year = {}
for r in inventory_rows:
    sid = r["supplier_id"]
    yr = r["date"][:4]
    key = (sid, yr)
    sup_by_year.setdefault(key, {"total": 0, "short": 0})
    sup_by_year[key]["total"] += 1
    if r["units_received"] < r["units_ordered"] * 0.95:
        sup_by_year[key]["short"] += 1

print(f"=== GENERATE SYNTHETIC DATA SUMMARY ===")
print(f"store_inventory.csv rows:     {total_inv:,}")
print(f"sales_transactions.json rows: {total_sales:,}")
print(f"weather_disruptions.json events: {len(events)}")
print(f"")
print(f"Mean spoilage rate:  {mean_sp:.3f} ({mean_sp*100:.1f}%)")
print(f"Max spoilage rate:   {max_sp:.3f} ({max_sp*100:.1f}%)")
print(f"")
print(f"Spoilage by region:")
for reg, val in sorted(region_means.items()):
    print(f"  {reg}: {val*100:.1f}%")
print(f"")
print(f"Strawberry April spike (NE, >20% spoilage): {len(strwbry_ne_april)} rows")
print(f"")
print(f"Supplier late rate trend (unreliable suppliers):")
for sup in ("SUP-0001", "SUP-0002", "SUP-0003"):
    for yr in ("2025", "2026"):
        k = (sup, yr)
        if k in sup_by_year and sup_by_year[k]["total"] > 0:
            rate = sup_by_year[k]["short"] / sup_by_year[k]["total"]
            print(f"  {sup} {yr}: {rate:.3f} ({rate*100:.1f}%)")
print(f"")
print(f"Warehouse temp failure dates: {[d.isoformat() for d in temp_fail_dates]}")
print(f"Lane spoilage configuration: {LANE_SPOILAGE}")
print(f"")
print(f"NOTE: Using catalog 'matt_fe_bar_catalog' (CREATE CATALOG not permitted on this metastore)")
print(f"Volume path: dbfs:/Volumes/matt_fe_bar_catalog/bronze/raw_landing/")
