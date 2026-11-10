# Databricks notebook source

# COMMAND ----------
# MAGIC %md # FreshGroove — Generate Supplier ASN PDFs
# MAGIC Generates 120 synthetic Advance Ship Notice PDFs and saves to Volume.
# MAGIC Catalog: matt_fe_bar_catalog (freshgroove_febar name requires CREATE CATALOG privilege)

# COMMAND ----------
%pip install fpdf2

# COMMAND ----------
import random
from datetime import date, timedelta
from fpdf import FPDF

random.seed(42)

VOLUME_PATH = "/Volumes/matt_fe_bar_catalog/bronze/raw_landing/supplier_asn_pdfs"
dbutils.fs.mkdirs(VOLUME_PATH)

SUPPLIERS = ["SUP-0001", "SUP-0002", "SUP-0003", "SUP-0004", "SUP-0005", "SUP-0006", "SUP-0007"]
CARRIERS = ["FedEx Freight", "UPS Supply Chain", "XPO Logistics", "J.B. Hunt", "Schneider National"]
LANES = ["truck", "rail", "ocean"]
SKUS = [f"SKU-PROD{i:02d}" for i in range(1,16)] + \
       [f"SKU-DAIRY{i:02d}" for i in range(1,13)] + \
       [f"SKU-BAKE{i:02d}" for i in range(1,11)] + \
       [f"SKU-PREP{i:02d}" for i in range(1,9)] + ["SKU-STRWBRY"]

START_DATE = date(2025, 4, 1)

late_count = 0
docs = []

for i in range(120):
    asn_num = f"ASN-{700000 + i:07d}"
    supplier = random.choice(SUPPLIERS)
    ship_date = START_DATE + timedelta(days=random.randint(0, 364))

    # Hero window: SUP-0001 PDFs dated 2025-03-25 to 2025-04-10 have high late rate
    is_hero = (supplier == "SUP-0001" and
               date(2025, 3, 25) <= ship_date <= date(2025, 4, 10))

    # 15% overall late; hero window ~70% late
    late_prob = 0.70 if is_hero else 0.15
    is_late = random.random() < late_prob
    if is_late:
        late_count += 1
        offset = random.randint(2, 4)
    else:
        offset = random.randint(-1, 1)

    promised_date = ship_date + timedelta(days=max(1, offset + random.randint(1,3)))
    carrier = random.choice(CARRIERS)
    lane = random.choice(LANES)

    num_items = random.randint(2, 6)
    items = [(random.choice(SKUS), random.randint(50, 300)) for _ in range(num_items)]
    total_units = sum(q for _, q in items)

    # Build PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "ADVANCE SHIP NOTICE", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)
    pdf.cell(0, 7, f"ASN Number:          {asn_num}", ln=True)
    pdf.cell(0, 7, f"Supplier ID:         {supplier}", ln=True)
    pdf.cell(0, 7, f"Ship Date:           {ship_date.isoformat()}", ln=True)
    pdf.cell(0, 7, f"Promised Delivery:   {promised_date.isoformat()}", ln=True)
    pdf.cell(0, 7, f"Carrier:             {carrier}", ln=True)
    pdf.cell(0, 7, f"Lane:                {lane}", ln=True)
    pdf.cell(0, 7, f"Risk Flag:           {'YES - LATE DELIVERY' if is_late else 'NO'}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Items:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for sku, qty in items:
        pdf.cell(0, 6, f"  {sku}: {qty} units", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Total Units: {total_units}", ln=True)

    path = f"{VOLUME_PATH}/{asn_num}.pdf"
    pdf.output(f"/tmp/{asn_num}.pdf")
    dbutils.fs.cp(f"file:///tmp/{asn_num}.pdf", path)
    docs.append({"asn": asn_num, "supplier": supplier, "is_late": is_late, "ship_date": str(ship_date)})

print(f"Generated {len(docs)} ASN PDFs")
print(f"Late delivery PDFs: {late_count} ({late_count/len(docs)*100:.1f}%)")
hero = [d for d in docs if d['supplier']=='SUP-0001' and '2025-03-25' <= d['ship_date'] <= '2025-04-10']
hero_late = [d for d in hero if d['is_late']]
print(f"Hero window (SUP-0001, Mar 25-Apr 10): {len(hero_late)} late out of {len(hero)} total")

# Show a sample late-delivery PDF
late_sample = next(d for d in docs if d["is_late"])
print(f"\nSample late delivery ASN: {late_sample['asn']} from {late_sample['supplier']}")

# COMMAND ----------
# Verify count in volume
files = dbutils.fs.ls(VOLUME_PATH)
print(f"PDFs in volume: {len(files)}")
display(spark.createDataFrame([{"asn": d["asn"], "supplier": d["supplier"], "is_late": d["is_late"]} for d in docs[:10]]))
