"""
Generate the SIMULATED retail dataset used by the dashboard.

The data is synthetic. It is modelled on a typical neighbourhood mini-market in
Seri Iskandar, Perak (near UTP), with Malaysian products, prices in RM, local
payment methods, the UTP semester calendar and Malaysian festive seasons.
It does NOT come from any real store.

Schema is based on common public retail datasets:
  - Kaggle "Supermarket Sales"  (invoice, product line, unit price, qty, payment, gross income)
  - UCI "Online Retail II"      (invoice-level lines, customer ID, cancellations/returns)

Run:  python data_generation/generate_dataset.py
Output (in data/):
  transactions.csv   - POS line items (raw, with realistic data-quality issues)
  products.csv       - product master with cost price, supplier and lead time
  customers.csv      - loyalty members
  inventory.csv      - stock on hand at the end of the period
  calendar_events.csv- festive seasons and UTP semester breaks used in the simulation
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
START, END = "2025-01-01", "2026-10-31"
BASE_INVOICES_PER_DAY = 165
OUT = Path(__file__).resolve().parents[1] / "data"

rng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------
# 1. Product catalogue
#    (name, brand, unit, price_rm, popularity, extra_qty_mean, return_risk, tag)
# --------------------------------------------------------------------------
CATALOGUE = {
    "Rice & Grains": [
        ("Beras Wangi 5kg", "Jasmine", "bag", 21.90, 6, 0.0, 1, ""),
        ("Beras Super Tempatan 10kg", "Faiza", "bag", 26.00, 4, 0.0, 1, ""),
        ("Beras Basmathi 1kg", "Faiza", "pack", 9.50, 1.5, 0.0, 1, ""),
        ("Oat Segera 500g", "Quaker", "pack", 8.90, 2, 0.0, 1, ""),
        ("Bihun 400g", "Cap Rusa", "pack", 3.20, 2.5, 0.3, 1, ""),
    ],
    "Cooking Essentials": [
        ("Minyak Masak 5kg", "Saji", "bottle", 31.90, 3.5, 0.0, 1, ""),
        ("Minyak Masak Paket 1kg", "Seri Murni", "pack", 2.50, 4, 0.5, 1, ""),
        ("Gula Pasir 1kg", "Prai", "pack", 2.85, 6, 0.3, 1, ""),
        ("Tepung Gandum 1kg", "Blue Key", "pack", 2.70, 4, 0.3, 1, ""),
        ("Garam Halus 500g", "Cap Kapal", "pack", 1.20, 2, 0.0, 1, ""),
        ("Kicap Manis 345ml", "Kipas Udang", "bottle", 4.20, 3.5, 0.1, 1, ""),
        ("Sos Cili 340g", "Life", "bottle", 3.90, 3, 0.1, 1, ""),
        ("Serbuk Kari Daging 250g", "Baba's", "pack", 5.60, 2.5, 0.0, 1, ""),
        ("Santan Kotak 200ml", "Kara", "box", 2.90, 3, 0.6, 1, "raya"),
        ("Bawang Merah 1kg", "Local", "kg", 7.50, 3.5, 0.0, 2, ""),
        ("Bawang Putih 500g", "Local", "pack", 5.20, 3, 0.0, 2, ""),
        ("Ikan Bilis 200g", "Cap Ikan", "pack", 8.90, 1.5, 0.0, 1, ""),
    ],
    "Instant Food": [
        ("Mi Segera Kari 5x79g", "Maggi", "pack", 6.80, 7, 0.4, 1, ""),
        ("Mi Segera Ayam 5x77g", "Maggi", "pack", 6.80, 5, 0.4, 1, ""),
        ("Mi Goreng Perisa Asli 5x80g", "Mamee Daebak", "pack", 9.90, 4, 0.3, 1, ""),
        ("Mi Cawan Tom Yam", "Cintan", "cup", 2.30, 5, 0.8, 1, ""),
        ("Bubur Segera Ayam", "Nissin", "cup", 2.90, 1.5, 0.3, 1, ""),
        ("Sardin Tin 425g", "Ayam Brand", "can", 7.90, 3, 0.2, 1, ""),
        ("Tuna Mayonis 160g", "Ayam Brand", "can", 5.50, 2.5, 0.2, 1, ""),
        ("Nasi Segera Rendang", "Brahim's", "pack", 8.50, 1.5, 0.1, 1, ""),
    ],
    "Beverages": [
        ("Air Mineral 1.5L", "Spritzer", "bottle", 1.90, 8, 0.8, 1, ""),
        ("Air Mineral 6x500ml", "Bleu", "pack", 6.20, 3, 0.1, 1, ""),
        ("Milo Kotak 200ml", "Nestle", "box", 2.40, 6, 0.8, 1, ""),
        ("Milo Serbuk 1kg", "Nestle", "pack", 20.90, 2.5, 0.0, 1, ""),
        ("Teh 100 Uncang", "BOH", "box", 10.50, 2.5, 0.0, 1, ""),
        ("Kopi O 3 dalam 1", "Aik Cheong", "pack", 11.90, 2.5, 0.0, 1, ""),
        ("Nescafe Tin 240ml", "Nestle", "can", 2.70, 4, 0.6, 1, ""),
        ("100 Plus 500ml", "F&N", "bottle", 2.80, 5, 0.6, 1, ""),
        ("Coca-Cola 320ml", "Coca-Cola", "can", 2.50, 4, 0.6, 1, ""),
        ("Teh Bunga 500ml", "Yeo's", "bottle", 2.40, 2.5, 0.4, 1, ""),
        ("Sirap Rose 2L", "Ros", "bottle", 6.90, 1.5, 0.1, 1, "raya"),
        ("Jus Oren 1L", "Peel Fresh", "box", 6.50, 2, 0.1, 2, ""),
    ],
    "Snacks & Confectionery": [
        ("Keropok Ikan 60g", "Twisties", "pack", 2.50, 5, 0.6, 1, ""),
        ("Kerepek Ubi Pedas 150g", "Local", "pack", 3.50, 3.5, 0.3, 1, ""),
        ("Biskut Krim Coklat", "Julie's", "pack", 4.90, 3.5, 0.2, 1, ""),
        ("Biskut Lemak Manis", "Hup Seng", "tin", 7.90, 2, 0.0, 1, ""),
        ("Coklat Bar 35g", "Cadbury", "bar", 3.50, 3.5, 0.5, 1, ""),
        ("Gula-gula Mentos", "Mentos", "roll", 1.80, 3, 0.4, 1, ""),
        ("Kacang Goreng 100g", "Tong Garden", "pack", 4.20, 2, 0.1, 1, ""),
        ("Wafer Coklat", "Tango", "pack", 2.20, 3, 0.4, 1, ""),
    ],
    "Dairy & Eggs": [
        ("Telur Gred A 30 biji", "Local", "tray", 13.50, 5, 0.0, 3, ""),
        ("Telur Gred C 10 biji", "Local", "pack", 3.90, 4, 0.1, 3, ""),
        ("Susu Segar 1L", "Dutch Lady", "carton", 7.90, 3, 0.1, 4, ""),
        ("Susu Pekat Manis 500g", "F&N", "can", 4.30, 3, 0.2, 1, ""),
        ("Yogurt Strawberi", "Marigold", "cup", 2.30, 2, 0.4, 4, ""),
        ("Mentega 250g", "Anchor", "block", 11.90, 1.2, 0.0, 3, "raya"),
        ("Keju Hiris 12 keping", "Kraft", "pack", 8.90, 1.2, 0.0, 3, ""),
    ],
    "Bakery": [
        ("Roti Putih", "Gardenia", "loaf", 3.90, 6, 0.1, 5, ""),
        ("Roti Wholemeal", "Gardenia", "loaf", 4.70, 2.5, 0.0, 5, ""),
        ("Roti Krim Pandan", "Massimo", "pack", 1.40, 4, 0.6, 5, ""),
        ("Kek Gulung Coklat", "Twiggies", "pack", 1.60, 3, 0.4, 5, ""),
    ],
    "Fresh Produce": [
        ("Ayam Segar 1 ekor", "Local", "kg", 13.50, 3, 0.0, 3, ""),
        ("Sayur Sawi 500g", "Cameron", "pack", 3.50, 3, 0.1, 4, ""),
        ("Tomato 500g", "Cameron", "pack", 4.20, 2.5, 0.0, 4, ""),
        ("Cili Merah 200g", "Local", "pack", 3.20, 2.5, 0.0, 4, ""),
        ("Pisang Berangan 1 sikat", "Local", "bunch", 6.50, 2.5, 0.0, 4, ""),
        ("Kentang 1kg", "Import", "kg", 5.90, 2.5, 0.0, 3, ""),
        ("Limau Kasturi 250g", "Local", "pack", 2.50, 1.5, 0.0, 4, ""),
    ],
    "Frozen Food": [
        ("Nuget Ayam 850g", "Ayamas", "pack", 15.90, 2.5, 0.0, 2, ""),
        ("Sosej Ayam 1kg", "Ramly", "pack", 13.90, 2, 0.0, 2, ""),
        ("Roti Canai Sejuk Beku 20pcs", "Kawan", "pack", 13.50, 2.5, 0.0, 2, ""),
        ("Karipap Sejuk Beku 20pcs", "Figo", "pack", 9.90, 1.5, 0.0, 2, ""),
        ("Ais Krim Kon", "Wall's", "cone", 3.50, 3, 0.4, 2, ""),
        ("Burger Daging 6pcs", "Ramly", "pack", 9.50, 1.5, 0.0, 2, ""),
    ],
    "Household": [
        ("Sabun Cuci Pinggan 900ml", "Sunlight", "bottle", 6.90, 3, 0.0, 1, ""),
        ("Serbuk Pencuci 2.3kg", "Breeze", "pack", 21.90, 1.8, 0.0, 1, ""),
        ("Pelembut Fabrik 1.6L", "Downy", "pack", 15.90, 1.5, 0.0, 1, ""),
        ("Tisu Gulung 10 gulung", "Premier", "pack", 12.90, 2.5, 0.0, 1, ""),
        ("Beg Sampah Besar 20pcs", "Glad", "pack", 5.90, 2, 0.0, 1, ""),
        ("Ubat Nyamuk Lingkaran", "Ridsect", "box", 5.50, 2, 0.0, 1, ""),
        ("Gas Tong 14kg (tukar)", "Petronas", "tank", 26.60, 0.8, 0.0, 1, ""),
        ("Bateri AA 4pcs", "Energizer", "pack", 11.90, 1, 0.0, 2, ""),
    ],
    "Personal Care": [
        ("Syampu 340ml", "Sunsilk", "bottle", 13.90, 1.5, 0.0, 1, ""),
        ("Sabun Mandi Cecair 900ml", "Lifebuoy", "bottle", 12.50, 1.8, 0.0, 1, ""),
        ("Ubat Gigi 225g", "Colgate", "tube", 7.90, 2, 0.0, 1, ""),
        ("Berus Gigi 3pcs", "Darlie", "pack", 9.90, 1, 0.0, 1, ""),
        ("Pencuci Muka 100g", "Garnier", "tube", 14.90, 1.2, 0.0, 2, ""),
        ("Deodoran Roll-On", "Nivea", "bottle", 11.90, 1.2, 0.0, 1, ""),
        ("Tuala Wanita 16pcs", "Kotex", "pack", 8.90, 1.5, 0.0, 1, ""),
        ("Pelitup Muka 50pcs", "Medicos", "box", 9.90, 0.8, 0.0, 1, ""),
    ],
    "Stationery & Student": [
        ("Pen Biru 3pcs", "Faber-Castell", "pack", 4.50, 2, 0.1, 1, ""),
        ("Buku Nota A4", "Campap", "pcs", 4.90, 1.8, 0.2, 1, ""),
        ("Kertas A4 500 helai", "Double A", "ream", 15.90, 1, 0.0, 1, ""),
        ("Pita Pembetul", "Pilot", "pcs", 5.50, 1, 0.0, 1, ""),
        ("Kabel USB-C", "Generic", "pcs", 12.90, 0.8, 0.0, 3, ""),
        ("Kad Tambah Nilai RM10", "Hotlink", "card", 10.00, 2.5, 0.0, 1, ""),
    ],
    "Festive & Seasonal": [
        ("Kurma Mariami 1kg", "Mariami", "box", 18.90, 0.0, 0.0, 1, "ramadan"),
        ("Kuih Raya Tart Nenas", "Local", "jar", 22.00, 0.0, 0.2, 2, "raya"),
        ("Biskut Raya Assorted Tin", "Khong Guan", "tin", 29.90, 0.0, 0.0, 1, "raya"),
        ("Sampul Duit Raya 20pcs", "Local", "pack", 3.50, 0.0, 0.5, 1, "raya"),
        ("Kulit Ketupat 10pcs", "Local", "pack", 4.50, 0.0, 0.3, 2, "raya"),
        ("Limau Mandarin 10 biji", "Import", "box", 15.90, 0.0, 0.0, 3, "cny"),
        ("Ang Pow 20pcs", "Local", "pack", 3.50, 0.0, 0.3, 1, "cny"),
        ("Pelita Minyak Tanah", "Local", "pcs", 6.90, 0.0, 0.3, 2, "raya"),
    ],
}

MARGIN = {  # gross margin on selling price
    "Rice & Grains": 0.08, "Cooking Essentials": 0.11, "Instant Food": 0.17,
    "Beverages": 0.22, "Snacks & Confectionery": 0.27, "Dairy & Eggs": 0.14,
    "Bakery": 0.18, "Fresh Produce": 0.26, "Frozen Food": 0.22, "Household": 0.24,
    "Personal Care": 0.29, "Stationery & Student": 0.36, "Festive & Seasonal": 0.32,
}
SUPPLIER = {  # fictional suppliers, lead time in days
    "Rice & Grains": ("Kinta Dry Goods Distributor", 5),
    "Cooking Essentials": ("Kinta Dry Goods Distributor", 5),
    "Instant Food": ("Perak FMCG Wholesale", 4),
    "Beverages": ("Perak FMCG Wholesale", 4),
    "Snacks & Confectionery": ("Perak FMCG Wholesale", 4),
    "Dairy & Eggs": ("Manjung Fresh Supply", 2),
    "Bakery": ("Bakery Route Delivery", 1),
    "Fresh Produce": ("Manjung Fresh Supply", 2),
    "Frozen Food": ("Ipoh Cold Chain Trading", 3),
    "Household": ("Ipoh Home & Care Supplies", 7),
    "Personal Care": ("Ipoh Home & Care Supplies", 7),
    "Stationery & Student": ("Seri Iskandar Stationery Hub", 6),
    "Festive & Seasonal": ("Ipoh Festive Trading", 10),
}

rows = []
pid = 1
for cat, items in CATALOGUE.items():
    for name, brand, unit, price, pop, xq, rr, tag in items:
        rows.append(dict(
            product_id=f"P{pid:03d}", product_name=name, category=cat, brand=brand,
            unit=unit, selling_price_rm=price,
            cost_price_rm=round(price * (1 - MARGIN[cat]) * rng.uniform(0.97, 1.03), 2),
            supplier=SUPPLIER[cat][0], lead_time_days=SUPPLIER[cat][1],
            _pop=pop, _xq=xq, _rr=rr, _tag=tag,
        ))
        pid += 1
products = pd.DataFrame(rows)

# Two products launched mid-period, one discontinued (realistic slow movers)
launch = {"Mi Goreng Perisa Asli 5x80g": "2025-06-01", "Kabel USB-C": "2025-09-01"}
discontinue = {"Bubur Segera Ayam": "2026-04-15"}

# --------------------------------------------------------------------------
# 2. Calendar: festive seasons and UTP semester breaks
# --------------------------------------------------------------------------
EVENTS = [
    ("2025-01-27", "2025-01-31", "Chinese New Year", "cny"),
    ("2025-03-01", "2025-03-29", "Ramadan", "ramadan"),
    ("2025-03-30", "2025-04-02", "Hari Raya Aidilfitri", "raya_day"),
    ("2025-06-05", "2025-06-08", "Hari Raya Haji", "haji"),
    ("2025-08-31", "2025-08-31", "Merdeka Day", "public"),
    ("2025-10-20", "2025-10-20", "Deepavali", "public"),
    ("2026-02-14", "2026-02-18", "Chinese New Year", "cny"),
    ("2026-02-19", "2026-03-19", "Ramadan", "ramadan"),
    ("2026-03-20", "2026-03-23", "Hari Raya Aidilfitri", "raya_day"),
    ("2026-05-26", "2026-05-29", "Hari Raya Haji", "haji"),
    ("2026-08-31", "2026-08-31", "Merdeka Day", "public"),
]
BREAKS = [  # assumed UTP semester breaks (students away)
    ("2025-01-01", "2025-01-12"), ("2025-04-19", "2025-05-18"),
    ("2025-08-16", "2025-09-14"), ("2025-12-13", "2026-01-11"),
    ("2026-04-18", "2026-05-17"), ("2026-08-15", "2026-09-13"),
]
calendar = pd.DataFrame(
    [(s, e, n, "Festive / public holiday") for s, e, n, _ in EVENTS]
    + [(s, e, "UTP semester break", "Semester break") for s, e in BREAKS],
    columns=["start_date", "end_date", "event", "event_type"],
)

days = pd.date_range(START, END, freq="D")


def in_ranges(d, ranges):
    return any(pd.Timestamp(s) <= d <= pd.Timestamp(e) for s, e in ranges)


def event_of(d):
    for s, e, n, k in EVENTS:
        if pd.Timestamp(s) <= d <= pd.Timestamp(e):
            return k
    return None


def pre_raya(d):
    """Last 10 days of Ramadan: heavy festive shopping."""
    for s, e, _, k in EVENTS:
        if k == "ramadan" and pd.Timestamp(e) - pd.Timedelta(days=9) <= d <= pd.Timestamp(e):
            return True
    return False


# --------------------------------------------------------------------------
# 3. Customers (loyalty members)
# --------------------------------------------------------------------------
N_MEMBERS = 2600
seg = rng.choice(["Student", "Resident", "Staff"], N_MEMBERS, p=[0.42, 0.44, 0.14])
join = pd.to_datetime(START) + pd.to_timedelta(
    np.where(rng.random(N_MEMBERS) < 0.55, 0, rng.integers(0, len(days) - 30, N_MEMBERS)), unit="D"
)
# some members stop coming (graduated / moved / switched store)
churn_days = rng.integers(60, len(days) + 200, N_MEMBERS)
churn = join + pd.to_timedelta(churn_days, unit="D")
churn = pd.Series(churn).where(rng.random(N_MEMBERS) < 0.38, pd.Timestamp("2099-01-01"))
rate = rng.gamma(1.4, 1.0, N_MEMBERS)  # visit propensity (heavy tail = loyal regulars)
age = np.where(
    seg == "Student", "18-24",
    np.where(seg == "Staff", rng.choice(["25-34", "35-44", "45-54"], N_MEMBERS),
             rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], N_MEMBERS, p=[.08, .27, .27, .22, .16])))
area = np.where(
    seg == "Student", rng.choice(["UTP Campus", "Seri Iskandar"], N_MEMBERS, p=[.7, .3]),
    rng.choice(["Seri Iskandar", "Bota", "Tronoh", "Parit", "Bandar Universiti"], N_MEMBERS,
               p=[.45, .15, .15, .1, .15]))
customers = pd.DataFrame(dict(
    customer_id=[f"M{i:05d}" for i in range(1, N_MEMBERS + 1)],
    segment=seg, gender=rng.choice(["Male", "Female"], N_MEMBERS),
    age_group=age, area=area, join_date=join.date,
))

# --------------------------------------------------------------------------
# 4. Demand model helpers
# --------------------------------------------------------------------------
CATS = list(CATALOGUE)
SEG_CAT = {  # category preference by shopper segment
    "Student":  dict(zip(CATS, [0.5, 0.6, 2.4, 2.4, 2.0, 0.7, 1.4, 0.3, 0.9, 0.6, 1.0, 1.6, 0.5])),
    "Resident": dict(zip(CATS, [1.6, 2.2, 1.0, 1.4, 1.0, 1.5, 1.1, 1.6, 1.2, 1.2, 0.9, 0.2, 0.6])),
    "Staff":    dict(zip(CATS, [1.1, 1.4, 1.2, 1.8, 1.2, 1.2, 1.2, 1.1, 1.1, 1.0, 1.0, 0.6, 0.6])),
}
HOURS = np.arange(8, 24)
HOUR_NORMAL = np.array([5, 6, 4, 4, 7, 8, 6, 4, 5, 7, 9, 10, 9, 7, 5, 3], float)
HOUR_RAMADAN = np.array([3, 3, 3, 3, 3, 3, 4, 6, 9, 12, 8, 6, 8, 9, 6, 4], float)
DOW = np.array([0.92, 0.88, 0.9, 0.95, 1.08, 1.2, 1.12])  # Mon..Sun

cat_index = {c: products.index[products.category == c].to_numpy() for c in CATS}
pop = products._pop.to_numpy(float)
tag = products._tag.to_numpy()


def product_weights(d):
    w = pop.copy()
    ev = event_of(d)
    if ev == "ramadan" or pre_raya(d):
        w[tag == "ramadan"] = 6
        w[tag == "raya"] += 4 if pre_raya(d) else 1.5
    elif ev == "raya_day":
        w[tag == "raya"] += 2
    if ev == "cny" or (d.month == 1 and d.day >= 20 and d.year == 2025) or \
            (d.year == 2026 and pd.Timestamp("2026-02-05") <= d <= pd.Timestamp("2026-02-18")):
        w[tag == "cny"] = 5
    for name, dt in launch.items():
        if d < pd.Timestamp(dt):
            w[products.product_name == name] = 0
    for name, dt in discontinue.items():
        if d >= pd.Timestamp(dt):
            w[products.product_name == name] = 0
    return w


def cat_probs(segment, d):
    p = np.array([SEG_CAT[segment][c] for c in CATS])
    if pre_raya(d):  # cooking + festive surge before Raya
        p[CATS.index("Cooking Essentials")] *= 1.8
        p[CATS.index("Festive & Seasonal")] *= 4
        p[CATS.index("Beverages")] *= 1.3
    if event_of(d) == "ramadan":
        p[CATS.index("Festive & Seasonal")] *= 2
    if in_ranges(d, [(s, e) for s, e in BREAKS[0:0]]):
        pass
    return p / p.sum()


PAY = ["Cash", "DuitNow QR", "Touch 'n Go eWallet", "Debit Card", "Credit Card"]


def pay_probs(segment, d):
    t = (d - pd.Timestamp(START)).days / len(days)  # cashless grows over time
    base = {
        "Student":  [0.18, 0.30, 0.40, 0.10, 0.02],
        "Resident": [0.48, 0.20, 0.12, 0.14, 0.06],
        "Staff":    [0.25, 0.27, 0.18, 0.18, 0.12],
    }[segment]
    p = np.array(base)
    p[0] *= 1 - 0.30 * t
    p[1] *= 1 + 0.35 * t
    return p / p.sum()


# --------------------------------------------------------------------------
# 5. Simulate POS transactions day by day
# --------------------------------------------------------------------------
prices = products.selling_price_rm.to_numpy()
xq = products._xq.to_numpy()
cust_seg = customers.segment.to_numpy()
cust_join = pd.to_datetime(customers.join_date).to_numpy()
cust_churn = churn.to_numpy()

frames = []
inv_no = 100000
for d in days:
    ev = event_of(d)
    on_break = in_ranges(d, BREAKS)
    growth = 1 + 0.06 * (d - pd.Timestamp(START)).days / 365
    factor = DOW[d.dayofweek] * growth
    if ev == "raya_day":
        factor *= 0.55  # people balik kampung
    elif pre_raya(d):
        factor *= 1.35
    elif ev == "cny":
        factor *= 0.95
    elif ev in ("haji", "public"):
        factor *= 1.05
    if on_break:
        factor *= 0.72  # students away
    if d.day >= 25 or d.day <= 3:
        factor *= 1.08  # payday
    n = rng.poisson(BASE_INVOICES_PER_DAY * factor)

    # who is shopping
    is_member = rng.random(n) < 0.56
    active = (cust_join <= d.to_datetime64()) & (cust_churn > d.to_datetime64())
    wts = rate * active * np.where((cust_seg == "Student") & on_break, 0.15, 1.0)
    member_ids = rng.choice(len(customers), is_member.sum(), p=wts / wts.sum())
    walkin_seg = rng.choice(["Student", "Resident", "Staff"], (~is_member).sum(),
                            p=[0.22, 0.68, 0.10] if on_break else [0.45, 0.45, 0.10])
    cid = np.full(n, None, dtype=object)
    segs = np.empty(n, dtype=object)
    cid[is_member] = customers.customer_id.to_numpy()[member_ids]
    segs[is_member] = cust_seg[member_ids]
    segs[~is_member] = walkin_seg

    # time of day
    hp = HOUR_RAMADAN if ev == "ramadan" else HOUR_NORMAL
    hrs = rng.choice(HOURS, n, p=hp / hp.sum())
    mins = rng.integers(0, 60, n)

    # payment per invoice
    pay = np.array([rng.choice(PAY, p=pay_probs(s, d)) for s in segs])

    # basket lines
    n_lines = 1 + rng.poisson(np.where(is_member, 2.4, 1.6))
    w_prod = product_weights(d)
    line_inv = np.repeat(np.arange(n), n_lines)
    line_seg = segs[line_inv]
    line_prod = np.empty(len(line_inv), dtype=int)
    for s in ("Student", "Resident", "Staff"):
        m = line_seg == s
        if not m.any():
            continue
        cp = cat_probs(s, d)
        cats = rng.choice(len(CATS), m.sum(), p=cp)
        out = np.empty(m.sum(), dtype=int)
        for ci in np.unique(cats):
            idx = cat_index[CATS[ci]]
            pw = w_prod[idx]
            if pw.sum() == 0:  # e.g. festive items out of season -> fall back to snacks
                idx = cat_index["Snacks & Confectionery"]
                pw = w_prod[idx]
            k = cats == ci
            out[k] = rng.choice(idx, k.sum(), p=pw / pw.sum())
        line_prod[m] = out

    qty = 1 + rng.poisson(xq[line_prod])
    price_now = prices[line_prod] * (1.035 if d.year == 2026 else 1.0)  # 2026 price increase
    price_now = np.round(price_now, 2)

    df = pd.DataFrame(dict(inv=line_inv, product_idx=line_prod, quantity=qty, unit_price_rm=price_now))
    df = df.groupby(["inv", "product_idx", "unit_price_rm"], as_index=False)["quantity"].sum()

    # weekly promotion: 8 random products at 10% off (fresh pick each ISO week)
    wk_rng = np.random.default_rng(d.isocalendar().week + 100 * d.year)
    promo = wk_rng.choice(len(products), 8, replace=False)
    disc = np.where(np.isin(df.product_idx, promo), 0.10, 0.0)
    df["discount_rm"] = np.round(df.unit_price_rm * df.quantity * disc, 2)

    inv_ids = np.array([f"INV{inv_no + i}" for i in range(n)])
    inv_no += n
    df["invoice_no"] = inv_ids[df.inv]
    df["date"] = d.date()
    df["time"] = [f"{h:02d}:{m:02d}" for h, m in zip(hrs[df.inv], mins[df.inv])]
    df["customer_id"] = cid[df.inv]
    df["customer_type"] = np.where(is_member[df.inv], "Member", "Walk-in")
    df["payment_method"] = pay[df.inv]
    frames.append(df)

tx = pd.concat(frames, ignore_index=True)
tx["invoice_type"] = "Sale"
tx["return_reason"] = ""

# --------------------------------------------------------------------------
# 6. Returns (about 1% of lines; fresh / dairy / bakery return more often)
# --------------------------------------------------------------------------
rr = products._rr.to_numpy()[tx.product_idx]
ret_mask = rng.random(len(tx)) < 0.0028 * rr
ret = tx[ret_mask].copy()
ret["date"] = (pd.to_datetime(ret.date) + pd.to_timedelta(rng.integers(0, 6, len(ret)), unit="D")).dt.date
ret = ret[pd.to_datetime(ret.date) <= pd.Timestamp(END)]
ret["quantity"] = -np.minimum(ret.quantity, rng.integers(1, 3, len(ret)))
ret["discount_rm"] = 0.0
ret["invoice_type"] = "Return"
ret["invoice_no"] = "RTN" + ret.invoice_no.str[3:]
perishable = np.isin(products.category.to_numpy()[ret.product_idx],
                     ["Dairy & Eggs", "Bakery", "Fresh Produce", "Frozen Food"])
ret["return_reason"] = np.where(
    perishable,
    rng.choice(["Expired / near expiry", "Spoiled / damaged", "Wrong item"], len(ret), p=[.55, .35, .10]),
    rng.choice(["Damaged packaging", "Wrong item", "Faulty item", "Customer changed mind"], len(ret),
               p=[.40, .25, .15, .20]))
ret["time"] = [f"{h:02d}:{m:02d}" for h, m in zip(rng.integers(9, 22, len(ret)), rng.integers(0, 60, len(ret)))]
tx = pd.concat([tx, ret], ignore_index=True)

tx["line_total_rm"] = np.round(tx.unit_price_rm * tx.quantity - tx.discount_rm, 2)
tx["product_id"] = products.product_id.to_numpy()[tx.product_idx]
tx["product_name"] = products.product_name.to_numpy()[tx.product_idx]
tx["category"] = products.category.to_numpy()[tx.product_idx]

# --------------------------------------------------------------------------
# 7. Realistic POS data-quality issues (to be cleaned in the dashboard)
# --------------------------------------------------------------------------
n_tx = len(tx)
blank = rng.random(n_tx) < 0.002            # missing product name
tx.loc[blank, "product_name"] = ""
dups = tx.sample(frac=0.0015, random_state=SEED)  # POS double-scan duplicates
tx = pd.concat([tx, dups], ignore_index=True)
test_rows = tx.sample(12, random_state=1).copy()  # cashier test scans at RM0
test_rows["unit_price_rm"] = 0.0
test_rows["line_total_rm"] = 0.0
test_rows["invoice_no"] = "TEST" + test_rows.invoice_no.str[3:]
tx = pd.concat([tx, test_rows], ignore_index=True)

tx = tx.sort_values(["date", "time", "invoice_no"]).reset_index(drop=True)
tx = tx[["invoice_no", "invoice_type", "date", "time", "customer_id", "customer_type",
         "product_id", "product_name", "category", "quantity", "unit_price_rm",
         "discount_rm", "line_total_rm", "payment_method", "return_reason"]]

# --------------------------------------------------------------------------
# 8. Inventory snapshot at END (some low stock, some overstock)
# --------------------------------------------------------------------------
last90 = tx[(pd.to_datetime(tx.date) > pd.Timestamp(END) - pd.Timedelta(days=90)) & (tx.invoice_type == "Sale")]
avg_daily = last90.groupby("product_id").quantity.sum() / 90
avg_daily = avg_daily.reindex(products.product_id).fillna(0)
cover_days = rng.uniform(4, 28, len(products))
low = rng.random(len(products)) < 0.14
cover_days[low] = rng.uniform(0.3, 2.5, low.sum())
over = (~low) & (rng.random(len(products)) < 0.07)  # over-ordered items
cover_days[over] = rng.uniform(48, 75, over.sum())
stock = np.round(avg_daily.to_numpy() * cover_days).astype(int)
dead = avg_daily.to_numpy() < 0.05
stock[dead] = rng.integers(8, 60, dead.sum())  # leftover festive / discontinued stock
inventory = pd.DataFrame(dict(
    product_id=products.product_id, stock_on_hand=stock,
    last_stock_count_date=END,
))

# --------------------------------------------------------------------------
# 9. Save
# --------------------------------------------------------------------------
OUT.mkdir(exist_ok=True)
products.drop(columns=[c for c in products if c.startswith("_")]).to_csv(OUT / "products.csv", index=False)
customers.to_csv(OUT / "customers.csv", index=False)
inventory.to_csv(OUT / "inventory.csv", index=False)
calendar.to_csv(OUT / "calendar_events.csv", index=False)
tx.to_csv(OUT / "transactions.csv", index=False)

sales = tx[tx.invoice_type == "Sale"]
print(f"transactions: {len(tx):,} lines | invoices: {sales.invoice_no.nunique():,} | "
      f"revenue RM{sales.line_total_rm.sum():,.0f} | returns: {(tx.invoice_type == 'Return').sum():,}")
print(f"products: {len(products)} | members: {len(customers)} | days: {len(days)}")
