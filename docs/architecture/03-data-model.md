# Data Model — FreshGroove FE Bar

## Raw Sources (Volume: matt_fe_bar_catalog.bronze.raw_landing)

| Source | Format | Rows | Description |
|--------|--------|------|-------------|
| store_inventory/ | CSV | 201,480 | Store × SKU × day inventory, spoilage, supplier |
| sales_transactions/ | JSON | 201,480 | Store × SKU × day units sold |
| weather_disruptions/ | JSON | 25 | Supply disruption events with region/severity |
| supplier_asn_pdfs/ | PDF | 120 | Advance Ship Notices with risk flags |

## Key Fields

**store_inventory.csv:** date, store_id, sku_id, sku_name, category, on_hand_units, units_ordered, units_received, spoilage_units, supplier_id, region, warehouse_temp_ok

**sales_transactions.json:** date, store_id, sku_id, units_sold, unit_price

**weather_disruptions.json:** event_date, event_type, region, severity, supply_impact_pct, description

**ASN PDFs:** ASN Number, Supplier ID, Ship Date, Promised Delivery Date, Carrier, Lane, Items, Total Units, Risk Flag

## Schema Structure

Catalog: `matt_fe_bar_catalog` (workspace-provisioned; equivalent to `freshgroove_febar` in architecture)

| Schema | Purpose |
|--------|---------|
| bronze | Raw Delta tables from Volume (no transformation) |
| silver | Cleaned, joined, DQ-enforced tables |
| gold | Business-ready aggregations + ML feature tables |
| ml | Registered ML models (@prod, @challenger aliases) |

## Injected Signals

- **Strawberry (SKU-STRWBRY) at Northeast stores:** April demand spike +40%, SUP-0001 65% short shipment rate → 73 rows with >20% spoilage in April 2025
- **Unreliable suppliers (SUP-0001/02/03):** late rate rising from ~22% (2025) to ~27% (2026)
- **Warehouse temp failures:** 3 events (2025-07-12, 2025-10-12, 2025-10-24), dairy SKUs get 3× spoilage that week
- **Lane spoilage:** ocean=14%, rail=12%, truck=10%
- **Seasonality:** bakery +35% Nov-Dec, produce +20% Apr-Jun, strawberry +40% Apr (Northeast)
